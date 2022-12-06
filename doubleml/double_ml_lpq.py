import numpy as np
from scipy.optimize import root_scalar
from sklearn.utils.multiclass import type_of_target
from sklearn.base import clone
from sklearn.utils import check_X_y
from sklearn.model_selection import KFold, train_test_split

from .double_ml import DoubleML
from .double_ml_score_mixins import NonLinearScoreMixin
from ._utils import _dml_cv_predict, _trimm
from .double_ml_data import DoubleMLData


class DoubleMLLPQ(NonLinearScoreMixin, DoubleML):
    """Double machine learning for local potential quantiles

    Parameters
    ----------
    obj_dml_data : :class:`DoubleMLData` object
        The :class:`DoubleMLData` object providing the data and specifying the variables for the causal model.

    ml_m : classifier implementing ``fit()`` and ``predict()``
        A machine learner implementing ``fit()`` and ``predict_proba()`` methods (e.g.
        :py:class:`sklearn.ensemble.RandomForestClassifier`) for the propensity nuisance functions.

    treatment : int
        Binary treatment indicator. Has to be either ``0`` or ``1``. Determines the potential outcome to be considered.
        Default is ``1``.

    quantile : float
        Quantile of the potential outcome. Has to be between ``0`` and ``1``.
        Default is ``0.5``.

    n_folds : int
        Number of folds.
        Default is ``5``.

    n_rep : int
        Number of repetitons for the sample splitting.
        Default is ``1``.

    score : str
        A str (``'PQ'`` is the only choice) specifying the score function
        for potential quantiles.
        Default is ``'PQ'``.

    dml_procedure : str
        A str (``'dml1'`` or ``'dml2'``) specifying the double machine learning algorithm.
        Default is ``'dml2'``.

    trimming_rule : str
        A str (``'truncate'`` is the only choice) specifying the trimming approach.
        Default is ``'truncate'``.

    trimming_threshold : float
        The threshold used for trimming.
        Default is ``1e-12``.

    h : float or None
        The bandwidth to be used for the kernel density estimation of the score derivative.
        If ``None`` the bandwidth will be set to ``np.power(n_obs, -0.2)``, where ``n_obs`` is
        the number of observations in the sample.
        Default is ``1e-12``.

    normalize : bool
        Indicates whether to normalize weights in the estimation of the score derivative.
        Default is ``True``.

    draw_sample_splitting : bool
        Indicates whether the sample splitting should be drawn during initialization of the object.
        Default is ``True``.

    apply_cross_fitting : bool
        Indicates whether cross-fitting should be applied(``True`` is the only choice).
        Default is ``True``.
    """

    def __init__(self,
                 obj_dml_data,
                 ml_m,
                 treatment,
                 quantile=0.5,
                 n_folds=5,
                 n_rep=1,
                 score='LPQ',
                 dml_procedure='dml2',
                 trimming_rule='truncate',
                 trimming_threshold=1e-12,
                 h=None,
                 normalize=True,
                 draw_sample_splitting=True,
                 apply_cross_fitting=True):
        super().__init__(obj_dml_data,
                         n_folds,
                         n_rep,
                         score,
                         dml_procedure,
                         draw_sample_splitting,
                         apply_cross_fitting)

        self._quantile = quantile
        self._treatment = treatment
        self._h = h
        if self.h is None:
            self._h = np.power(self._dml_data.n_obs, -0.2)
        self._normalize = normalize

        if self._is_cluster_data:
            raise NotImplementedError('Estimation with clustering not implemented.')
        self._check_data(self._dml_data)
        self._check_score(self.score)
        self._check_quantile(self.quantile)
        self._check_treatment(self.treatment)
        self._check_bandwidth(self.h)
        if not isinstance(self.normalize, bool):
            raise TypeError('Normalization indicator has to be boolean. ' +
                            f'Object of type {str(type(self.normalize))} passed.')

        # initialize starting values and bounds
        y_treat = self._dml_data.y[self._dml_data.d == self.treatment]
        self._coef_bounds = (y_treat.min(), y_treat.max())
        self._coef_start_val = np.quantile(y_treat, self.quantile)

        # initialize and check trimming
        self._trimming_rule = trimming_rule
        self._trimming_threshold = trimming_threshold
        self._check_trimming()

        _ = self._check_learner(ml_m, 'ml_m', regressor=False, classifier=True)
        self._learner = {'ml_pi_z': clone(ml_m),
                         'ml_pi_du_z0': clone(ml_m), 'ml_pi_du_z1': clone(ml_m),
                         'ml_pi_d_z0': clone(ml_m), 'ml_pi_d_z1': clone(ml_m)}
        self._predict_method = {'ml_g': 'predict_proba', 'ml_m': 'predict_proba',
                                'ml_pi_z': 'predict_proba',
                                'ml_pi_du_z0': 'predict_proba', 'ml_pi_du_z1': 'predict_proba',
                                'ml_pi_d_z0': 'predict_proba', 'ml_pi_d_z1': 'predict_proba'}

        self._initialize_ml_nuisance_params()

    @property
    def quantile(self):
        """
        Quantile for potential outcome.
        """
        return self._quantile

    @property
    def treatment(self):
        """
        Treatment indicator for potential outcome.
        """
        return self._treatment

    @property
    def h(self):
        """
        The bandwidth the kernel density estimation of the derivative.
        """
        return self._h

    @property
    def normalize(self):
        """
        Indicates of the weights in the derivative estimation should be normalized.
        """
        return self._normalize

    @property
    def trimming_rule(self):
        """
        Specifies the used trimming rule.
        """
        return self._trimming_rule

    @property
    def trimming_threshold(self):
        """
        Specifies the used trimming threshold.
        """
        return self._trimming_threshold

    @property
    def _score_element_names(self):
        return ['ind_d', 'pi_z', 'pi_du_z0', 'pi_du_z1', 'y', 'z', 'comp_prob']

    def _compute_ipw_score(self, theta, d, y, prop, z, comp_prob):
        sign = 2 * self.treatment - 1.0
        weights = sign * (z / prop - (1 - z) / (1 - prop)) / comp_prob
        u = (d == self._treatment) * (y <= theta)
        v = -1. * self.quantile
        score = weights * u + v
        return score

    def _compute_score(self, psi_elements, coef, inds=None):
        sign = 2 * self.treatment - 1.0
        ind_d = psi_elements['ind_d']
        pi_z = psi_elements['pi_z']
        pi_du_z0 = psi_elements['pi_du_z0']
        pi_du_z1 = psi_elements['pi_du_z1']
        y = psi_elements['y']
        z = psi_elements['z']
        comp_prob = psi_elements['comp_prob']

        if inds is not None:
            ind_d = psi_elements['ind_d'][inds]
            pi_z = psi_elements['pi_z']
            pi_du_z0 = psi_elements['pi_du_z0'][inds]
            pi_du_z1 = psi_elements['pi_du_z1'][inds]
            y = psi_elements['y'][inds]
            z = psi_elements['z'][inds]

        score1 = pi_du_z1 - pi_du_z0
        score2 = (z / pi_z) * (ind_d * (y <= coef) - pi_du_z1)
        score3 = (1 - z) / (1 - pi_z) * (ind_d * (y <= coef) - pi_du_z0)
        score = sign * (score1 + score2 - score3) / comp_prob - self.quantile
        return score

    def _compute_score_deriv(self, psi_elements, coef, inds=None):
        sign = 2 * self.treatment - 1.0
        ind_d = psi_elements['ind_d']
        y = psi_elements['y']
        pi_z = psi_elements['pi_z']
        z = psi_elements['z']
        comp_prob = psi_elements['comp_prob']

        if inds is not None:
            ind_d = psi_elements['ind_d'][inds]
            y = psi_elements['y'][inds]
            pi_z = psi_elements['pi_z'][inds]
            z = psi_elements['z'][inds]

        score_weights = sign * ((z / pi_z) - (1 - z) / (1 - pi_z)) * ind_d / comp_prob
        normalization = score_weights.mean()
        if self._normalize:
            score_weights /= normalization

        u = (y - coef).reshape(-1, 1) / self._h
        kernel_est = np.exp(-1. * np.power(u, 2) / 2) / np.sqrt(2 * np.pi)
        deriv = np.multiply(score_weights, kernel_est.reshape(-1, )) / self._h

        return deriv

    def _initialize_ml_nuisance_params(self):
        self._params = {learner: {key: [None] * self.n_rep for key in self._dml_data.d_cols}
                        for learner in ['ml_pi_z', 'ml_pi_du_z0', 'ml_pi_du_z1',
                                        'ml_pi_d_z0', 'ml_pi_d_z1']}

    def _nuisance_est(self, smpls, n_jobs_cv, return_models=False):
        x, y = check_X_y(self._dml_data.x, self._dml_data.y,
                         force_all_finite=False)
        x, d = check_X_y(x, self._dml_data.d,
                         force_all_finite=False)
        x, z = check_X_y(x, np.ravel(self._dml_data.z),
                         force_all_finite=False)

        # initialize nuisance predictions
        pi_z_hat = np.full(shape=self._dml_data.n_obs, fill_value=np.nan)
        pi_d_z0_hat = np.full(shape=self._dml_data.n_obs, fill_value=np.nan)
        pi_d_z1_hat = np.full(shape=self._dml_data.n_obs, fill_value=np.nan)
        pi_du_z0_hat = np.full(shape=self._dml_data.n_obs, fill_value=np.nan)
        pi_du_z1_hat = np.full(shape=self._dml_data.n_obs, fill_value=np.nan)

        ipw_vec = np.full(shape=self.n_folds, fill_value=np.nan)
        # caculate nuisance functions over different folds
        for i_fold in range(self.n_folds):
            train_inds = smpls[i_fold][0]
            test_inds = smpls[i_fold][1]

            # start nested crossfitting
            train_inds_1, train_inds_2 = train_test_split(train_inds, test_size=0.5, random_state=42)
            smpls_prelim = [(train, test) for train, test in KFold(n_splits=self.n_folds).split(train_inds_1)]

            d_train_1 = d[train_inds_1]
            y_train_1 = y[train_inds_1]
            x_train_1 = x[train_inds_1, :]
            z_train_1 = z[train_inds_1]

            # preliminary propensity for z
            pi_z_hat_prelim = _dml_cv_predict(self._learner['ml_pi_z'], x_train_1, z_train_1,
                                              method='predict_proba', smpls=smpls_prelim)['preds']
            pi_z_hat_prelim = _trimm(pi_z_hat_prelim, self.trimming_rule, self.trimming_threshold)

            # todo add extra fold loop
            # propensity for d == 1 cond. on z == 0 (training set 1)
            x_z0_train_1 = x_train_1[z_train_1 == 0, :]
            d_z0_train_1 = d_train_1[z_train_1 == 0]
            self._learner['ml_pi_d_z0'].fit(x_z0_train_1, d_z0_train_1)
            pi_d_z0_hat_prelim = self._learner['ml_pi_d_z0'].predict_proba(x_train_1)[:, 1]
            pi_d_z0_hat_prelim = _trimm(pi_d_z0_hat_prelim, self.trimming_rule, self.trimming_threshold)

            # propensity for d == 1 cond. on z == 1 (training set 1)
            x_z1_train_1 = x_train_1[z_train_1 == 1, :]
            d_z1_train_1 = d_train_1[z_train_1 == 1]
            self._learner['ml_pi_d_z1'].fit(x_z1_train_1, d_z1_train_1)
            pi_d_z1_hat_prelim = self._learner['ml_pi_d_z1'].predict_proba(x_train_1)[:, 1]
            pi_d_z1_hat_prelim = _trimm(pi_d_z1_hat_prelim, self.trimming_rule, self.trimming_threshold)

            # preliminary estimate of theta_2_aux
            comp_prob_prelim = np.mean(pi_d_z1_hat_prelim - pi_d_z0_hat_prelim
                                       + z_train_1 / pi_z_hat_prelim * (d_train_1 - pi_d_z1_hat_prelim)
                                       - (1 - z_train_1) / (1 - pi_z_hat_prelim) * (d_train_1 - pi_d_z0_hat_prelim))

            # preliminary ipw estimate
            def ipw_score(theta):
                res = np.mean(self._compute_ipw_score(theta, d_train_1, y_train_1, pi_z_hat_prelim,
                                                      z_train_1, comp_prob_prelim))
                return res

            def get_bracket_guess(coef_start, coef_bounds):
                max_bracket_length = coef_bounds[1] - coef_bounds[0]
                b_guess = coef_bounds
                delta = 0.1
                s_different = False
                while (not s_different) & (delta <= 1.0):
                    a = np.maximum(coef_start - delta * max_bracket_length / 2, coef_bounds[0])
                    b = np.minimum(coef_start + delta * max_bracket_length / 2, coef_bounds[1])
                    b_guess = (a, b)
                    f_a = ipw_score(b_guess[0])
                    f_b = ipw_score(b_guess[1])
                    s_different = (np.sign(f_a) != np.sign(f_b))
                    delta += 0.1
                return s_different, b_guess

            _, bracket_guess = get_bracket_guess(self._coef_start_val, self._coef_bounds)

            root_res = root_scalar(ipw_score,
                                   bracket=bracket_guess,
                                   method='brentq')
            ipw_est = root_res.root
            ipw_vec[i_fold] = ipw_est

            # use the preliminary estimates to fit the nuisance parameters on train_2
            d_train_2 = d[train_inds_2]
            y_train_2 = y[train_inds_2]
            x_train_2 = x[train_inds_2, :]
            z_train_2 = z[train_inds_2]

            # propensity for (D == treatment)*Ind(Y <= ipq_est) cond. on z == 0
            x_z0_train_2 = x_train_2[z_train_2 == 0, :]
            du_z0_train_2 = (d_train_2[z_train_2 == 0] == self._treatment) * (y_train_2[z_train_2 == 0] <= ipw_est)
            self._learner['ml_pi_du_z0'].fit(x_z0_train_2, du_z0_train_2)
            pi_du_z0_hat[test_inds] = self._learner['ml_pi_du_z0'].predict_proba(x[test_inds, :])[:, 1]

            # propensity for (D == treatment)*Ind(Y <= ipq_est) cond. on z == 1
            x_z1_train_2 = x_train_2[z_train_2 == 1, :]
            du_z1_train_2 = (d_train_2[z_train_2 == 1] == self._treatment) * (y_train_2[z_train_2 == 1] <= ipw_est)
            self._learner['ml_pi_du_z1'].fit(x_z1_train_2, du_z1_train_2)
            pi_du_z1_hat[test_inds] = self._learner['ml_pi_du_z1'].predict_proba(x[test_inds, :])[:, 1]

            # refit nuisance elements for the local potential quantile
            z_train = z[train_inds]
            x_train = x[train_inds]
            d_train = d[train_inds]

            # refit propensity for z (whole training set)
            self._learner['ml_pi_z'].fit(x_train, z_train)
            pi_z_hat[test_inds] = self._learner['ml_pi_z'].predict_proba(x[test_inds, :])[:, 1]

            # refit propensity for d == 1 cond. on z == 0 (whole training set)
            x_z0_train = x_train[z_train == 0, :]
            d_z0_train = d_train[z_train == 0]
            self._learner['ml_pi_d_z0'].fit(x_z0_train, d_z0_train)
            pi_d_z0_hat[test_inds] = self._learner['ml_pi_d_z0'].predict_proba(x[test_inds, :])[:, 1]

            # propensity for d == 1 cond. on z == 1 (whole training set)
            x_z1_train = x_train[z_train == 1, :]
            d_z1_train = d_train[z_train == 1]
            self._learner['ml_pi_d_z1'].fit(x_z1_train, d_z1_train)
            pi_d_z1_hat[test_inds] = self._learner['ml_pi_d_z1'].predict_proba(x[test_inds, :])[:, 1]

        # clip propensities
        pi_z_hat = _trimm(pi_z_hat, self.trimming_rule, self.trimming_threshold)
        pi_d_z0_hat = _trimm(pi_d_z0_hat, self.trimming_rule, self.trimming_threshold)
        pi_d_z1_hat = _trimm(pi_d_z1_hat, self.trimming_rule, self.trimming_threshold)
        pi_du_z0_hat = _trimm(pi_du_z0_hat, self.trimming_rule, self.trimming_threshold)
        pi_du_z1_hat = _trimm(pi_du_z1_hat, self.trimming_rule, self.trimming_threshold)

        # estimate final nuisance parameter
        comp_prob_hat = np.mean(pi_d_z1_hat - pi_d_z0_hat
                                + z / pi_z_hat * (d - pi_d_z1_hat)
                                - (1 - z) / (1 - pi_z_hat) * (d - pi_d_z0_hat))

        # readjust start value for minimization
        self._coef_start_val = np.mean(ipw_vec)

        psi_elements = {'ind_d': d == self._treatment, 'pi_z': pi_z_hat,
                        'pi_du_z0': pi_du_z0_hat, 'pi_du_z1': pi_du_z1_hat,
                        'y': y, 'z': z, 'comp_prob': comp_prob_hat}
        preds = {'ml_pi_z': pi_z_hat,
                 'ml_pi_d_z0': pi_d_z0_hat, 'ml_pi_d_z1': pi_d_z1_hat,
                 'ml_pi_du_z0': pi_du_z0_hat, 'ml_pi_du_z1': pi_du_z1_hat}
        return psi_elements, preds

    def _nuisance_tuning(self, smpls, param_grids, scoring_methods, n_folds_tune, n_jobs_cv,
                         search_mode, n_iter_randomized_search):
        raise NotImplementedError('Nuisance tuning not implemented for potential quantiles.')

    def _check_score(self, score):
        valid_score = ['LPQ']
        if isinstance(score, str):
            if score not in valid_score:
                raise ValueError('Invalid score ' + score + '. ' +
                                 'Valid score ' + ' or '.join(valid_score) + '.')
        else:
            raise TypeError('Invalid score. ' +
                            'Valid score ' + ' or '.join(valid_score) + '.')
        return

    def _check_data(self, obj_dml_data):
        if not isinstance(obj_dml_data, DoubleMLData):
            raise TypeError('The data must be of DoubleMLData type. '
                            f'{str(obj_dml_data)} of type {str(type(obj_dml_data))} was passed.')
        one_treat = (obj_dml_data.n_treat == 1)
        binary_treat = (type_of_target(obj_dml_data.d) == 'binary')
        zero_one_treat = np.all((np.power(obj_dml_data.d, 2) - obj_dml_data.d) == 0)
        if not (one_treat & binary_treat & zero_one_treat):
            raise ValueError('Incompatible data. '
                             'To fit an LPQ model with DML '
                             'exactly one binary variable with values 0 and 1 '
                             'needs to be specified as treatment variable.')
        one_instr = (obj_dml_data.n_instr == 1)
        err_msg = ('Incompatible data. '
                   'To fit an IIVM model with DML '
                   'exactly one binary variable with values 0 and 1 '
                   'needs to be specified as instrumental variable.')
        if one_instr:
            binary_instr = (type_of_target(obj_dml_data.z) == 'binary')
            zero_one_instr = np.all((np.power(obj_dml_data.z, 2) - obj_dml_data.z) == 0)
            if not (one_instr & binary_instr & zero_one_instr):
                raise ValueError(err_msg)
        else:
            raise ValueError(err_msg)
        return

    def _check_quantile(self, quantile):
        if not isinstance(quantile, float):
            raise TypeError('Quantile has to be a float. ' +
                            f'Object of type {str(type(quantile))} passed.')

        if (quantile <= 0) | (quantile >= 1):
            raise ValueError('Quantile has be between 0 or 1. ' +
                             f'Quantile {str(quantile)} passed.')

    def _check_treatment(self, treatment):
        if not isinstance(treatment, int):
            raise TypeError('Treatment indicator has to be an integer. ' +
                            f'Object of type {str(type(treatment))} passed.')

        if (treatment != 0) & (treatment != 1):
            raise ValueError('Treatment indicator has be either 0 or 1. ' +
                             f'Treatment indicator {str(treatment)} passed.')

    def _check_bandwidth(self, bandwidth):
        if not isinstance(bandwidth, float):
            raise TypeError('Bandwidth has to be a float. ' +
                            f'Object of type {str(type(bandwidth))} passed.')

        if bandwidth <= 0:
            raise ValueError('Bandwidth has be positive. ' +
                             f'Bandwidth {str(bandwidth)} passed.')

    def _check_trimming(self):
        valid_trimming_rule = ['truncate']
        if self.trimming_rule not in valid_trimming_rule:
            raise ValueError('Invalid trimming_rule ' + str(self.trimming_rule) + '. ' +
                             'Valid trimming_rule ' + ' or '.join(valid_trimming_rule) + '.')
        if not isinstance(self.trimming_threshold, float):
            raise TypeError('trimming_threshold has to be a float. ' +
                            f'Object of type {str(type(self.trimming_threshold))} passed.')
        if (self.trimming_threshold <= 0) | (self.trimming_threshold >= 0.5):
            raise ValueError('Invalid trimming_threshold ' + str(self.trimming_threshold) + '. ' +
                             'trimming_threshold has to be between 0 and 0.5.')

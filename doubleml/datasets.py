import pandas as pd
import numpy as np

from scipy.linalg import toeplitz

from sklearn.datasets import make_spd_matrix

from .double_ml_data import DoubleMLData


def fetch_401K():
    url = 'https://github.com/VC2015/DMLonGitHub/raw/master/sipp1991.dta'
    data = pd.read_stata(url)
    return data


def fetch_bonus():
    url = 'https://raw.githubusercontent.com/VC2015/DMLonGitHub/master/penn_jae.dat'
    data = pd.read_csv(url, delim_whitespace=True)
    return data


def g(x):
    return np.power(np.sin(x), 2)


def m(x, nu=0., gamma=1.):
    return 0.5/np.pi*(np.sinh(gamma))/(np.cosh(gamma)-np.cos(x-nu))


def m2(x):
    return np.power(x, 2)


def m3(x, nu=0., gamma=1.):
    return 1./np.pi*(np.sinh(gamma))/(np.cosh(gamma)-np.cos(x-nu))


_array_alias = ['array', 'np.ndarray', 'np.array', np.ndarray]
_data_frame_alias = ['DataFrame', 'pd.DataFrame', pd.DataFrame]
_dml_data_alias = ['DoubleMLData', DoubleMLData]


def make_plr_CCDDHNR2018(n_obs=500, dim_x=20, alpha=0.5, return_type='DoubleMLData', **kwargs):
    """
    Generates data from a partially linear regression model used in Chernozhukov et al. (2018) for Figure 1.
    The data generating process is defined as

    .. math::

        d_i = m_0(x_i) + s_1 v_i, & &v_i \\sim \\mathcal{N}(0,1),

        y_i = \\alpha d_i + g_0(x_i) + s_2 \\zeta_i, & &\\zeta_i \\sim \\mathcal{N}(0,1),


    with covariates :math:`x_i \\sim \\mathcal{N}(0, \\Sigma)`, where  :math:`\\Sigma` is a matrix with entries
    :math:`\\Sigma_{kj} = 0.7^{|j-k|}`.
    The nuisance functions are given by

    .. math::

        m_0(x_i) &= a_0 x_{i,1} + a_1 \\frac{\\exp(x_{i,3})}{1+\\exp(x_{i,3})},

        g_0(X) &= b_0 \\frac{\\exp(x_{i,1})}{1+\\exp(x_{i,1})} + b_1 x_{i,3}.

    Parameters
    ----------
    n_obs :
        The number of observations to simulate.
    dim_x :
        The number of covariates.
    alpha :
        The value of the causal parameter.
    return_type :
        .. include:: ../../shared/dgp/return_type.rst
    **kwargs
        Additional keyword arguments to set non-default values for the parameters
        :math:`a_0=1`, :math:`a_1=0.25`, :math:`s_1=1`, :math:`b_0=1`, :math:`b_1=0.25` or :math:`s_2=1`.

    References
    ----------
    Chernozhukov, V., Chetverikov, D., Demirer, M., Duflo, E., Hansen, C., Newey, W. and Robins, J. (2018), Double/debiased machine learning for treatment and structural parameters. The Econometrics Journal, 21: C1-C68. doi:`10.1111/ectj.12097 <https://doi.org/10.1111/ectj.12097>`_.
    """
    a_0 = kwargs.get('a_0', 1.)
    a_1 = kwargs.get('a_1', 0.25)
    s_1 = kwargs.get('s_1', 1.)

    b_0 = kwargs.get('b_0', 1.)
    b_1 = kwargs.get('b_1', 0.25)
    s_2 = kwargs.get('s_2', 1.)

    cov_mat = toeplitz([np.power(0.7, k) for k in range(dim_x)])
    x = np.random.multivariate_normal(np.zeros(dim_x), cov_mat, size=[n_obs, ])

    d = a_0 * x[:, 0] + a_1 * np.divide(np.exp(x[:, 2]), 1 + np.exp(x[:, 2])) \
        + s_1 * np.random.standard_normal(size=[n_obs, ])
    y = alpha * d + b_0 * np.divide(np.exp(x[:, 2]), 1 + np.exp(x[:, 2])) \
        + b_1 * x[:, 2] + s_2 * np.random.standard_normal(size=[n_obs, ])

    if return_type in _array_alias:
        return x, y, d
    elif return_type in _data_frame_alias + _dml_data_alias:
        x_cols = [f'X{i + 1}' for i in np.arange(dim_x)]
        data = pd.DataFrame(np.column_stack((x, y, d)),
                            columns=x_cols + ['y', 'd'])
        if return_type in _data_frame_alias:
            return data
        else:
            return DoubleMLData(data, 'y', 'd', x_cols)
    else:
        raise ValueError('invalid return_type')


def make_plr_turrell2018(n_obs=100, dim_x=20, theta=0.5, return_type='DoubleMLData', **kwargs):
    """
    Generates data from a partially linear regression model used in blog article by Turrell (2018).
    The data generating process is defined as

    .. math::

        d_i = m_0(x_i' b) + v_i, & &v_i \\sim \\mathcal{N}(0,1),

        y_i = \\theta d_i + g_0(x_i' b) + u_i, & &u_i \\sim \\mathcal{N}(0,1),


    with covariates :math:`x_i \\sim \\mathcal{N}(0, \\Sigma)`, where  :math:`\\Sigma` is a random symmetric,
    positive-definite matrix generated with :py:meth:`sklearn.datasets.make_spd_matrix`.
    :math:`b` is a vector with entries :math:`b_j=\\frac{1}{j}` and the nuisance functions are given by

    .. math::

        m_0(x) &= \\frac{1}{2 \\pi} \\frac{\\sinh(\\gamma)}{\\cosh(\\gamma) - \\cos(x-\\nu)},

        g_0(x) &= \\sin(x)^2.

    Parameters
    ----------
    n_obs :
        The number of observations to simulate.
    dim_x :
        The number of covariates.
    theta :
        The value of the causal parameter.
    return_type :
        .. include:: ../../shared/dgp/return_type.rst
    **kwargs
        Additional keyword arguments to set non-default values for the parameters
        :math:`\\nu=0`, or :math:`\\gamma=1`.

    References
    ----------
    Turrell, A. (2018), Econometrics in Python part I - Double machine learning, Markov Wanderer: A blog on economics, science, coding and data. `http://aeturrell.com/2018/02/10/econometrics-in-python-partI-ML/ <http://aeturrell.com/2018/02/10/econometrics-in-python-partI-ML/>`_.
    """
    nu = kwargs.get('nu', 0.)
    gamma = kwargs.get('gamma', 1.)

    b = [1 / k for k in range(1, dim_x + 1)]
    sigma = make_spd_matrix(dim_x)

    X = np.random.multivariate_normal(np.zeros(dim_x), sigma, size=[n_obs, ])
    G = g(np.dot(X, b))
    M = m(np.dot(X, b), nu=nu, gamma=gamma)
    d = M + np.random.standard_normal(size=[n_obs, ])
    y = np.dot(theta, d) + G + np.random.standard_normal(size=[n_obs, ])

    if return_type in _array_alias:
        return X, y, d
    elif return_type in _data_frame_alias + _dml_data_alias:
        x_cols = [f'X{i + 1}' for i in np.arange(dim_x)]
        data = pd.DataFrame(np.column_stack((X, y, d)),
                            columns=x_cols + ['y', 'd'])
        if return_type in _data_frame_alias:
            return data
        else:
            return DoubleMLData(data, 'y', 'd', x_cols)
    else:
        raise ValueError('invalid return_type')


def make_pliv_data(n_obs=100, dim_x=20, theta=0.5, gamma_z=0.4, return_type='DoubleMLData'):
    b = [1/k for k in range(1, dim_x+1)]
    sigma = make_spd_matrix(dim_x)

    X = np.random.multivariate_normal(np.zeros(dim_x), sigma, size=[n_obs, ])
    G = g(np.dot(X, b))
    # instrument
    Z = m(np.dot(X, b)) + np.random.standard_normal(size=[n_obs, ])
    # treatment
    M = m(gamma_z * Z + np.dot(X, b))
    D = M + np.random.standard_normal(size=[n_obs, ])
    Y = np.dot(theta, D) + G + np.random.standard_normal(size=[n_obs, ])

    if return_type in _array_alias:
        return X, Y, D, Z
    elif return_type in _data_frame_alias + _dml_data_alias:
        x_cols = [f'X{i + 1}' for i in np.arange(dim_x)]
        data = pd.DataFrame(np.column_stack((X, Y, D, Z)),
                            columns=x_cols + ['y', 'd', 'z'])
        if return_type in _data_frame_alias:
            return data
        else:
            return DoubleMLData(data, 'y', 'd', x_cols, 'z')
    else:
        raise ValueError('invalid return_type')


def make_irm_data(n_obs=100, dim_x=20, theta=0.5, return_type='DoubleMLData'):
    b = [1/k for k in range(1, dim_x+1)]
    sigma = make_spd_matrix(dim_x)

    X = np.random.multivariate_normal(np.zeros(dim_x), sigma, size=[n_obs, ])
    G = g(np.dot(X, b))
    M = m3(np.dot(X, b))
    MM = M + np.random.standard_normal(size=[n_obs, ])
    MMM = np.maximum(np.minimum(MM, 0.99), 0.01)
    d = np.random.binomial(p=MMM, n=1)
    y = np.dot(theta, d) + G + np.random.standard_normal(size=[n_obs, ])

    if return_type in _array_alias:
        return X, y, d
    elif return_type in _data_frame_alias + _dml_data_alias:
        x_cols = [f'X{i + 1}' for i in np.arange(dim_x)]
        data = pd.DataFrame(np.column_stack((X, y, d)),
                            columns=x_cols + ['y', 'd'])
        if return_type in _data_frame_alias:
            return data
        else:
            return DoubleMLData(data, 'y', 'd', x_cols)
    else:
        raise ValueError('invalid return_type')


def make_iivm_data(n_obs=100, dim_x=20, theta=0.5, gamma_z=0.4, return_type='DoubleMLData'):
    b = [1/k for k in range(1, dim_x+1)]
    sigma = make_spd_matrix(dim_x)

    X = np.random.multivariate_normal(np.zeros(dim_x), sigma, size=[n_obs, ])
    G = g(np.dot(X, b))
    # instrument
    M1 = m3(np.dot(X, b))
    MM = M1 + np.random.standard_normal(size=[n_obs, ])
    MMM = np.maximum(np.minimum(MM, 0.99), 0.01)
    Z = np.random.binomial(p=MMM, n=1)
    # treatment
    M = m3(gamma_z * Z + np.dot(X, b))
    MM = M + np.random.standard_normal(size=[n_obs, ])
    MMM = np.maximum(np.minimum(MM, 0.99), 0.01)
    D = np.random.binomial(p=MMM, n=1)

    Y = np.dot(theta, D) + G + np.random.standard_normal(size=[n_obs, ])

    if return_type in _array_alias:
        return X, Y, D, Z
    elif return_type in _data_frame_alias + _dml_data_alias:
        x_cols = [f'X{i + 1}' for i in np.arange(dim_x)]
        data = pd.DataFrame(np.column_stack((X, Y, D, Z)),
                            columns=x_cols + ['y', 'd', 'z'])
        if return_type in _data_frame_alias:
            return data
        else:
            return DoubleMLData(data, 'y', 'd', x_cols, 'z')
    else:
        raise ValueError('invalid return_type')


def make_pliv_CHS2015(n_obs, alpha=1., dim_x=200, dim_z=150, return_type='DoubleMLData'):
    """
    Generates data from a partially linear IV regression model used in Chernozhukov, Hansen and Spindler (2015).
    The data generating process is defined as

    .. math::

        z_i &= \\Pi x_i + \\zeta_i,

        d_i &= x_i' \\gamma + z_i' \\delta + u_i,

        y_i &= \\alpha d_i + x_i' \\beta + \\varepsilon_i,

    with

    .. math::

        \\left(\\begin{matrix} \\varepsilon_i \\\\ u_i \\\\ \\zeta_i \\\\ x_i \\end{matrix} \\right) \\sim \\mathcal{N}\\left(0, \\left(\\begin{matrix} 1 & 0.6 & 0 & 0 \\\\ 0.6 & 1 & 0 & 0 \\\\ 0 & 0 & 0.25 I_{p_n^z} & 0 \\\\ 0 & 0 & 0 & \\Sigma \\end{matrix} \\right) \\right)

    where  :math:`\\Sigma` is a :math:`p_n^x \\times p_n^x` matrix with entries
    :math:`\\Sigma_{kj} = 0.5^{|j-k|}` and :math:`I_{p_n^z}` is the :math:`p_n^z \\times p_n^z` identity matrix.
    :math:`\\beta = \\gamma` is a :math:`p_n^x`-vector with entries :math:`\\beta_j=\\frac{1}{j^2}`,
    :math:`\\delta` is a :math:`p_n^z`-vector with entries :math:`\\delta_j=\\frac{1}{j^2}`
    and :math:`\\Pi = (I_{p_n^z}, 0_{p_n^z \\times (p_n^x - p_n^z)})`.

    Parameters
    ----------
    n_obs :
        The number of observations to simulate.
    alpha :
        The value of the causal parameter.
    dim_x :
        The number of covariates.
    dim_z :
        The number of instruments.
    return_type :
        .. include:: ../../shared/dgp/return_type.rst

    References
    ----------
    Chernozhukov, V., Hansen, C. and Spindler, M. (2015), Post-Selection and Post-Regularization Inference in Linear Models with Many Controls and Instruments. American Economic Review: Papers and Proceedings, 105 (5): 486-90.
    """
    assert dim_x >= dim_z
    # see https://assets.aeaweb.org/asset-server/articles-attachments/aer/app/10505/P2015_1022_app.pdf
    xx = np.random.multivariate_normal(np.zeros(2),
                                       np.array([[1., 0.6], [0.6, 1.]]),
                                       size=[n_obs, ])
    epsilon = xx[:,0]
    u = xx[:,1]

    sigma = toeplitz([np.power(0.5, k) for k in range(0, dim_x)])
    X = np.random.multivariate_normal(np.zeros(dim_x),
                                      sigma,
                                      size=[n_obs, ])

    I_z = np.eye(dim_z)
    xi = np.random.multivariate_normal(np.zeros(dim_z),
                                       0.25*I_z,
                                       size=[n_obs, ])

    beta = [1 / (k**2) for k in range(1, dim_x + 1)]
    gamma = beta
    delta = [1 / (k**2) for k in range(1, dim_z + 1)]
    Pi = np.hstack((I_z, np.zeros((dim_z, dim_x-dim_z))))

    Z = np.dot(X, np.transpose(Pi)) + xi
    D = np.dot(X, gamma) + np.dot(Z, delta) + u
    Y = alpha * D + np.dot(X, beta) + epsilon

    if return_type in _array_alias:
        return X, Y, D, Z
    elif return_type in _data_frame_alias + _dml_data_alias:
        x_cols = [f'X{i + 1}' for i in np.arange(dim_x)]
        z_cols = [f'Z{i + 1}' for i in np.arange(dim_z)]
        data = pd.DataFrame(np.column_stack((X, Y, D, Z)),
                            columns=x_cols + ['y', 'd'] + z_cols)
        if return_type in _data_frame_alias:
            return data
        else:
            return DoubleMLData(data, 'y', 'd', x_cols, z_cols)
    else:
        raise ValueError('invalid return_type')

    return data


def make_pliv_multiway_cluster_CKMS2019(N=25, M=25, dim_X=100, theta=1., return_type='DoubleMLData', **kwargs):
    """
    Generates data from a partially linear IV regression model with multiway cluster sample used in Chiang et al. (2019).
    The data generating process is defined as

    .. math::

        Z_{ij} &= X_{ij}' \\xi_0 + V_{ij},

        D_{ij} &= Z_{ij}' \\pi_{10} + X_{ij}' \\pi_{20} + v_{ij},

        Y_{ij} &= D_{ij} \\theta + X_{ij}' \\zeta_0 + \\varepsilon_{ij},

    with

    .. math::

        X_{ij} &= (1 - \\omega_1^X - \\omega_2^X) \\alpha_{ij}^X + \\omega_1^X \\alpha_{i}^X + \\omega_2^X \\alpha_{j}^X,

        \\varepsilon_{ij} &= (1 - \\omega_1^\\varepsilon - \\omega_2^\\varepsilon) \\alpha_{ij}^\\varepsilon + \\omega_1^\\varepsilon \\alpha_{i}^\\varepsilon + \\omega_2^\\varepsilon \\alpha_{j}^\\varepsilon,

        v_{ij} &= (1 - \\omega_1^v - \\omega_2^v) \\alpha_{ij}^v + \\omega_1^v \\alpha_{i}^v + \\omega_2^v \\alpha_{j}^v,

        V_{ij} &= (1 - \\omega_1^V - \\omega_2^V) \\alpha_{ij}^V + \\omega_1^V \\alpha_{i}^V + \\omega_2^V \\alpha_{j}^V,

    and :math:`\\alpha_{ij}^X, \\alpha_{i}^X, \\alpha_{j}^X \\sim \\mathcal{N}(0, \\Sigma)`
    where  :math:`\\Sigma` is a :math:`p_x \\times p_x` matrix with entries
    :math:`\\Sigma_{kj} = s_X^{|j-k|}`.
    Further

    .. math::

        \\left(\\begin{matrix} \\alpha_{ij}^\\varepsilon \\\\ \\alpha_{ij}^v \\end{matrix}\\right), \\left(\\begin{matrix} \\alpha_{i}^\\varepsilon \\\\ \\alpha_{i}^v \\end{matrix}\\right), \\left(\\begin{matrix} \\alpha_{j}^\\varepsilon \\\\ \\alpha_{j}^v \\end{matrix}\\right) \\sim \\mathcal{N}\\left((0, \\left(\\begin{matrix} 1 & s_{\\varepsilon v} \\\\ s_{\\varepsilon v} & 1 \\end{matrix} \\right) \\right)


    and :math:`\\alpha_{ij}^V, \\alpha_{i}^V, \\alpha_{j}^V \\sim \\mathcal{N}(0, 1)`.

    Parameters
    ----------
    N :
        The number of observations (first dimension).
    M :
        The number of observations (second dimension).
    dim_X :
        The number of covariates.
    theta :
        The value of the causal parameter.
    return_type :
        If ``'DoubleMLData'`` or ``DoubleMLData``, returns a ``DoubleMLData`` object where ``DoubleMLData.data`` is a ``pd.DataFrame`` with multiindex.

        If ``'DataFrame'``, ``'pd.DataFrame'`` or ``pd.DataFrame``, returns a ``pd.DataFrame`` with multiindex.
    **kwargs
        Additional keyword arguments to set non-default values for the parameters
        :math:`\\pi_{10}=1.0`, :math:`\\omega_X = \\omega_{\\varepsilon} = \\omega_V = \\omega_v = (0.25, 0.25)`,
        :math:`s_X = s_{\\varepsilon v} = 0.25`,
        or the :math:`p_x`-vectors :math:`\\zeta_0 = \\pi_{20} = \\xi_0` with default entries :math:`(\\zeta_{0})_j = 0.5^j`.

    References
    ----------
    Chiang, H. D., Kato K., Ma, Y. and Sasaki, Y. (2019), Multiway Cluster Robust Double/Debiased Machine Learning, arXiv:`1909.03489 <https://arxiv.org/abs/1909.03489>`_.
    """
    # additional parameters specifiable via kwargs
    pi_10 = kwargs.get('pi_10', 1.0)

    xx = np.arange(1, dim_X + 1)
    zeta_0 = kwargs.get('zeta_0', np.power(0.5, xx))
    pi_20 = kwargs.get('pi_20', np.power(0.5, xx))
    xi_0 = kwargs.get('xi_0', np.power(0.5, xx))

    omega_X = kwargs.get('omega_X', np.array([0.25, 0.25]))
    omega_epsilon = kwargs.get('omega_epsilon', np.array([0.25, 0.25]))
    omega_v = kwargs.get('omega_v', np.array([0.25, 0.25]))
    omega_V = kwargs.get('omega_V', np.array([0.25, 0.25]))

    s_X = kwargs.get('s_X', 0.25)
    s_epsilon_v = kwargs.get('s_epsilon_v', 0.25)

    # use np.tile() and np.repeat() for repeating vectors in different styles, i.e.,
    # np.tile([v1, v2, v3], 2) [v1, v2, v3, v1, v2, v3]
    # np.repeat([v1, v2, v3], 2) [v1, v1, v2, v2, v3, v3]

    alpha_V = np.random.normal(size=(N * M))
    alpha_V_i = np.repeat(np.random.normal(size=N), M)
    alpha_V_j = np.tile(np.random.normal(size=M), N)

    cov_mat = np.array([[1, s_epsilon_v], [s_epsilon_v, 1]])
    alpha_eps_v = np.random.multivariate_normal(np.zeros(2), cov_mat, size=[N * M, ])
    alpha_eps = alpha_eps_v[:, 0]
    alpha_v = alpha_eps_v[:, 1]

    alpha_eps_v_i = np.random.multivariate_normal(np.zeros(2), cov_mat, size=[N, ])
    alpha_eps_i = np.repeat(alpha_eps_v_i[:, 0], M)
    alpha_v_i = np.repeat(alpha_eps_v_i[:, 1], M)

    alpha_eps_v_j = np.random.multivariate_normal(np.zeros(2), cov_mat, size=[M, ])
    alpha_eps_j = np.tile(alpha_eps_v_j[:, 0], N)
    alpha_v_j = np.tile(alpha_eps_v_j[:, 1], N)

    cov_mat = toeplitz([np.power(s_X, k) for k in range(dim_X)])
    alpha_X = np.random.multivariate_normal(np.zeros(dim_X), cov_mat, size=[N * M, ])
    alpha_X_i = np.repeat(np.random.multivariate_normal(np.zeros(dim_X), cov_mat, size=[N, ]),
                          M, axis=0)
    alpha_X_j = np.tile(np.random.multivariate_normal(np.zeros(dim_X), cov_mat, size=[M, ]),
                        (N, 1))

    # generate variables
    X = (1 - omega_X[0] - omega_X[1]) * alpha_X \
        + omega_X[0] * alpha_X_i + omega_X[1] * alpha_X_j

    eps = (1 - omega_epsilon[0] - omega_epsilon[1]) * alpha_eps \
          + omega_epsilon[0] * alpha_eps_i + omega_epsilon[1] * alpha_eps_j

    v = (1 - omega_v[0] - omega_v[1]) * alpha_v \
        + omega_v[0] * alpha_v_i + omega_v[1] * alpha_v_j

    V = (1 - omega_V[0] - omega_V[1]) * alpha_V \
        + omega_V[0] * alpha_V_i + omega_V[1] * alpha_V_j

    Z = np.matmul(X, xi_0) + V
    D = Z * pi_10 + np.matmul(X, pi_20) + v
    Y = D * theta + np.matmul(X, zeta_0) + eps

    ind = pd.MultiIndex.from_product([range(N), range(M)])

    if return_type in _data_frame_alias + _dml_data_alias:
        x_cols = [f'X{i + 1}' for i in np.arange(dim_X)]
        data = pd.DataFrame(np.column_stack((X, Y, D, Z)),
                            columns=x_cols + ['Y', 'D', 'Z'],
                            index=ind)
        if return_type in _data_frame_alias:
            return data
        else:
            return DoubleMLData(data, 'Y', 'D', x_cols, 'Z')
    else:
        raise ValueError('invalid return_type')

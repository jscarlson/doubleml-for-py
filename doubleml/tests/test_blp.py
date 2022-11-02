import numpy as np
import pandas as pd
import pytest

import doubleml as dml

from ._utils_blp_manual import fit_blp, blp_confint


@pytest.fixture(scope='module',
                params=[True, False])
def ci_joint(request):
    return request.param


@pytest.fixture(scope='module',
                params=[0.95, 0.9])
def ci_level(request):
    return request.param


@pytest.fixture(scope='module')
def dml_blp_fixture(ci_joint, ci_level):
    n = 50
    np.random.seed(42)
    random_basis = pd.DataFrame(np.random.normal(0, 1, size=(n, 3)))
    random_signal = np.random.normal(0, 1, size=(n, ))

    blp = dml.DoubleMLIRMBLP(random_signal, random_basis).fit()
    blp_manual = fit_blp(random_signal, random_basis)

    np.random.seed(42)
    ci = blp.confint(random_basis, joint=ci_joint, level=ci_level, n_rep_boot=1000)
    np.random.seed(42)
    ci_manual = blp_confint(blp_manual, random_basis, joint=ci_joint, level=ci_level, n_rep_boot=1000)

    res_dict = {'coef': blp.blp_model.params,
                'coef_manual': blp_manual.params,
                'values': blp.blp_model.fittedvalues,
                'values_manual':  blp_manual.fittedvalues,
                'omega': blp.blp_omega,
                'omega_manual': blp_manual.cov_HC0,
                'ci': ci,
                'ci_manual': ci_manual}

    return res_dict


@pytest.mark.ci
def test_dml_blp_coef(dml_blp_fixture):
    assert np.allclose(dml_blp_fixture['coef'],
                       dml_blp_fixture['coef_manual'],
                       rtol=1e-9, atol=1e-4)


@pytest.mark.ci
def test_dml_blp_values(dml_blp_fixture):
    assert np.allclose(dml_blp_fixture['values'],
                       dml_blp_fixture['values_manual'],
                       rtol=1e-9, atol=1e-4)


@pytest.mark.ci
def test_dml_blp_omega(dml_blp_fixture):
    assert np.allclose(dml_blp_fixture['omega'],
                       dml_blp_fixture['omega_manual'],
                       rtol=1e-9, atol=1e-4)


@pytest.mark.ci
def test_dml_blp_ci(dml_blp_fixture):
    assert np.allclose(dml_blp_fixture['ci'],
                       dml_blp_fixture['ci_manual'],
                       rtol=1e-9, atol=1e-4)

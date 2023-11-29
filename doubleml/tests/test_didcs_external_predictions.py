import numpy as np
import pytest
import math
from sklearn.linear_model import LinearRegression, LassoCV, LogisticRegression
from doubleml import DoubleMLData, DoubleMLDIDCS
from doubleml.datasets import make_did_SZ2020
from doubleml.utils import dummy_regressor, dummy_classifier
from ._utils import draw_smpls


@pytest.fixture(scope="module", params=["observational", "experimental"])
def did_score(request):
    return request.param


@pytest.fixture(scope="module", params=["dml1", "dml2"])
def dml_procedure(request):
    return request.param


@pytest.fixture(scope="module", params=[1, 3])
def n_rep(request):
    return request.param


@pytest.fixture(scope="module")
def doubleml_didcs_fixture(did_score, dml_procedure, n_rep):
    ext_predictions = {"d": {}}
    dml_data = make_did_SZ2020(n_obs=500, cross_sectional_data=True, return_type="DoubleMLData")
    all_smpls = draw_smpls(len(dml_data.y), 5, n_rep=n_rep, groups=dml_data.d)
    kwargs = {
        "obj_dml_data": dml_data,
        "score": did_score,
        "n_rep": n_rep,
        "n_folds": 5,
        "dml_procedure": dml_procedure,
        "draw_sample_splitting": False
    }
    DMLDIDCS = DoubleMLDIDCS(ml_g=LinearRegression(), ml_m=LogisticRegression(), **kwargs)
    DMLDIDCS.set_sample_splitting(all_smpls)
    np.random.seed(3141)
    DMLDIDCS.fit(store_predictions=True)

    ext_predictions["d"]["ml_g_d0_t0"] = DMLDIDCS.predictions["ml_g_d0_t0"][:, :, 0]
    ext_predictions["d"]["ml_g_d0_t1"] = DMLDIDCS.predictions["ml_g_d0_t1"][:, :, 0]
    ext_predictions["d"]["ml_g_d1_t0"] = DMLDIDCS.predictions["ml_g_d1_t0"][:, :, 0]
    ext_predictions["d"]["ml_g_d1_t1"] = DMLDIDCS.predictions["ml_g_d1_t1"][:, :, 0]
    ext_predictions["d"]["ml_m"] = DMLDIDCS.predictions["ml_m"][:, :, 0]

    DMLDIDCS_ext = DoubleMLDIDCS(ml_g=dummy_regressor(), ml_m=dummy_classifier(), **kwargs)
    DMLDIDCS_ext.set_sample_splitting(all_smpls)
    np.random.seed(3141)
    DMLDIDCS_ext.fit(external_predictions=ext_predictions)

    res_dict = {"coef_normal": DMLDIDCS.coef, "coef_ext": DMLDIDCS_ext.coef}

    return res_dict


@pytest.mark.ci
def test_doubleml_didcs_coef(doubleml_didcs_fixture):
    assert math.isclose(doubleml_didcs_fixture["coef_normal"], doubleml_didcs_fixture["coef_ext"], rel_tol=1e-9, abs_tol=1e-3)

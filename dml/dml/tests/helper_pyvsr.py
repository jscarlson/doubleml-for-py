from rpy2 import robjects
from rpy2.robjects import ListVector
from rpy2.robjects.vectors import IntVector


def export_smpl_split_to_r(smpls):
    n_smpls = len(smpls)
    all_train = ListVector.from_length(n_smpls)
    all_test = ListVector.from_length(n_smpls)

    for idx, (train, test) in enumerate(smpls):
        all_train[idx] = IntVector(train + 1)
        all_test[idx] = IntVector(test + 1)

    return all_train, all_test


# The R code to fit the DML model
r_MLPLR = robjects.r('''
        library('dml')
        library('mlr3learners')
        library('data.table')
        library('mlr3')

        f <- function(data, inf_model, dml_procedure, train_ids, test_ids) {
            data = data.table(data)
            mlmethod <- list(mlmethod_m = 'regr.lm',
                             mlmethod_g = 'regr.lm')
            params <- list(params_m = list(),
                           params_g = list())

            double_mlplr_obj = DoubleMLPLR$new(n_folds = 2,
                                     ml_learners = mlmethod,
                                     params = params,
                                     dml_procedure = dml_procedure, inf_model = inf_model)
            
            smpls = list(list(train_ids=train_ids, test_ids=test_ids))
            double_mlplr_obj$set_samples(smpls)
            
            double_mlplr_obj$fit(data, y = 'y', d = 'd')
            return(list(coef = double_mlplr_obj$coef,
                        se = double_mlplr_obj$se))
        }
        ''')


r_MLPLIV = robjects.r('''
        library('dml')
        library('mlr3learners')
        library('data.table')
        library('mlr3')

        f <- function(data, inf_model, dml_procedure, train_ids, test_ids) {
            data = data.table(data)
            mlmethod <- list(mlmethod_m = 'regr.lm',
                             mlmethod_g = 'regr.lm',
                             mlmethod_r = 'regr.lm')
            params <- list(params_m = list(),
                           params_g = list(),
                           params_r = list())

            double_mlpliv_obj = DoubleMLPLIV$new(n_folds = 2,
                                     ml_learners = mlmethod,
                                     params = params,
                                     dml_procedure = dml_procedure, inf_model = inf_model)
            
            smpls = list(list(train_ids=train_ids, test_ids=test_ids))
            double_mlpliv_obj$set_samples(smpls)
            
            double_mlpliv_obj$fit(data, y = 'y', d = 'd', z = 'z')
            return(list(coef = double_mlpliv_obj$coef,
                        se = double_mlpliv_obj$se))
        }
        ''')


r_IRM = robjects.r('''
        library('dml')
        library('mlr3learners')
        library('data.table')
        library('mlr3')

        f <- function(data, inf_model, dml_procedure, train_ids, test_ids) {
            data = data.table(data)
            mlmethod <- list(mlmethod_m = 'classif.log_reg',
                             mlmethod_g = 'regr.lm')
            params <- list(params_m = list(),
                           params_g = list())

            double_mlirm_obj = DoubleMLIRM$new(n_folds = 2,
                                     ml_learners = mlmethod,
                                     params = params,
                                     dml_procedure = dml_procedure, inf_model = inf_model)
            
            smpls = list(list(train_ids=train_ids, test_ids=test_ids))
            double_mlirm_obj$set_samples(smpls)
            
            double_mlirm_obj$fit(data, y = 'y', d = 'd')
            return(list(coef = double_mlirm_obj$coef,
                        se = double_mlirm_obj$se))
        }
        ''')


r_IIVM = robjects.r('''
        library('dml')
        library('mlr3learners')
        library('data.table')
        library('mlr3')

        f <- function(data, inf_model, dml_procedure, train_ids, test_ids) {
            data = data.table(data)
            mlmethod <- list(mlmethod_p = 'classif.log_reg',
                             mlmethod_mu = 'regr.lm',
                             mlmethod_m = 'classif.log_reg')
            params <- list(params_p = list(),
                           params_mu = list(),
                           params_m = list())

            double_mliivm_obj = DoubleMLIIVM$new(n_folds = 2,
                                     ml_learners = mlmethod,
                                     params = params,
                                     dml_procedure = dml_procedure, inf_model = inf_model)
            
            smpls = list(list(train_ids=train_ids, test_ids=test_ids))
            double_mliivm_obj$set_samples(smpls)
            
            double_mliivm_obj$fit(data, y = 'y', d = 'd', z = 'z')
            return(list(coef = double_mliivm_obj$coef,
                        se = double_mliivm_obj$se))
        }
        ''')


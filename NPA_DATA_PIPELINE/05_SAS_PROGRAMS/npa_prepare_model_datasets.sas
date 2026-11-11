/*==========================================================================
  PROJECT : NPA Early Detection - SAS Viya Pipeline
  PROGRAM : npa_prepare_model_datasets.sas
  PURPOSE : Assemble partitioned, Model Studio-ready datasets:
            - NPA_MODEL_TRAIN   (7,000 customers, with npa_flag)
            - NPA_MODEL_TEST    (3,000 customers, with npa_flag)
            - NPA_SCORING_INPUT (2,000 customers, unlabelled, NO target)
  ENVIRONMENT : SAS Viya for Learners / SAS Studio
==========================================================================*/

/*--------------------------------------------------------------------------
  1. MERGE DEVELOPMENT RECORDS WITH TARGET FROM FUTURE_OUTCOME
--------------------------------------------------------------------------*/
proc sql;
    create table work.model_data_staged as
    select f.*,
           fo.npa_flag
    from work.npa_features_with_flags as f
    left join work.future_outcome as fo
        on f.customer_id = fo.customer_id;
quit;

/*--------------------------------------------------------------------------
  2. PARTITION INTO TRAIN, TEST, AND SCORING DATASETS
--------------------------------------------------------------------------*/
data work.NPA_MODEL_TRAIN
     work.NPA_MODEL_TEST
     work.NPA_SCORING_INPUT(drop=npa_flag population_role split_set);
    set work.model_data_staged;

    if population_role = 'DEVELOPMENT' and split_set = 'TRAIN' then output work.NPA_MODEL_TRAIN;
    else if population_role = 'DEVELOPMENT' and split_set = 'TEST' then output work.NPA_MODEL_TEST;
    else if population_role = 'SCORING' and split_set = 'SCORING' then output work.NPA_SCORING_INPUT;
run;

/* Drop partition metadata columns from train and test as well */
data work.NPA_MODEL_TRAIN;
    set work.NPA_MODEL_TRAIN(drop=population_role split_set);
run;

data work.NPA_MODEL_TEST;
    set work.NPA_MODEL_TEST(drop=population_role split_set);
run;

/*--------------------------------------------------------------------------
  3. VERIFY SCHEMA AND POPULATION INTEGRITY
--------------------------------------------------------------------------*/
proc sql;
    select count(*) as train_count,
           sum(npa_flag) as train_npa_events,
           mean(npa_flag)*100 as train_npa_rate_pct
    from work.NPA_MODEL_TRAIN;

    select count(*) as test_count,
           sum(npa_flag) as test_npa_events,
           mean(npa_flag)*100 as test_npa_rate_pct
    from work.NPA_MODEL_TEST;

    select count(*) as scoring_count
    from work.NPA_SCORING_INPUT;
quit;

/* Check that no missing values exist in the target in Train or Test */
proc freq data=work.NPA_MODEL_TRAIN;
    tables npa_flag / missing;
run;

proc freq data=work.NPA_MODEL_TEST;
    tables npa_flag / missing;
run;

/*--------------------------------------------------------------------------
  4. EXPORT PREPARED MODEL DATASETS TO CSV AND CAS
--------------------------------------------------------------------------*/
%macro export_dataset(ds);
    proc export data=work.&ds
        outfile="&out_dir/&ds..csv"
        dbms=csv replace;
    run;

    %if &use_cas = 1 %then %do;
        proc casutil;
            droptable casdata="&ds" incaslib="&caslib" quiet;
            load data=work.&ds outcaslib="&caslib" casout="&ds" promote;
        quit;
        %put NOTE: Promoted &ds to CAS library &caslib;
    %end;
%mend export_dataset;

%export_dataset(NPA_MODEL_TRAIN);
%export_dataset(NPA_MODEL_TEST);
%export_dataset(NPA_SCORING_INPUT);

%put NOTE: npa_prepare_model_datasets.sas completed successfully.;


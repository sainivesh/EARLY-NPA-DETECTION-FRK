/*==========================================================================
  PROJECT : NPA Early Detection - SAS Viya Pipeline
  PROGRAM : npa_import_and_qa.sas
  PURPOSE : Import raw CSV synthetic datasets, customer split, and target into SAS,
            and perform data quality integrity checks.
  ENVIRONMENT : SAS Viya for Learners / SAS Studio

  INSTRUCTIONS:
  1. Upload the CSV files from NPA_DATA_PIPELINE folders to your SAS session folder.
  2. Set the &data_dir macro variable below to the folder path where the CSVs are placed.
  3. If CAS is available and desired, set &use_cas=1 and specify &caslib.
==========================================================================*/

/*--------------------------------------------------------------------------
  CONFIGURATION PARAMETERS
--------------------------------------------------------------------------*/
options mprint symbolgen noovp;

%let data_dir = /home/user/NPA_DATA_PIPELINE;  /* Path to uploaded datasets */
%let out_dir  = &data_dir/06_SAS_OUTPUTS;      /* Export directory */
%let use_cas  = 0;                             /* 0 = SAS WORK library, 1 = CAS Library */
%let caslib   = casuser;                       /* CAS library name if use_cas=1 */

/* Create output directory if it does not exist */
options dlcreatedir;
libname _out "&out_dir";
libname _out clear;
options nodlcreatedir;

/* Optional CAS Session setup */
%macro setup_cas;
    %if &use_cas = 1 %then %do;
        cas mycas sessopts=(caslib="&caslib" timeout=1800);
        libname caslib cas caslib="&caslib";
        %put NOTE: CAS session initialized with library caslib=&caslib;
    %end;
    %else %do;
        %put NOTE: Operating in standard SAS WORK library mode;
    %end;
%mend setup_cas;
%setup_cas;

/*--------------------------------------------------------------------------
  1. IMPORT RAW DATASETS
--------------------------------------------------------------------------*/
%macro import_csv(file, outds);
    proc import datafile="&data_dir/01_RAW_DATASETS/&file..csv"
        out=work.&outds dbms=csv replace;
        getnames=yes;
        guessingrows=max;
    run;
%mend import_csv;

%import_csv(customer_master, customer_master);
%import_csv(loan_account, loan_account);
%import_csv(emi_history, emi_history);
%import_csv(payment_history, payment_history);
%import_csv(credit_bureau, credit_bureau);
%import_csv(transaction_history, transaction_history);
%import_csv(NPA_History, NPA_History);
%import_csv(customer_company_details, customer_company_details);
%import_csv(npa_history_customer_summary, npa_history_customer_summary);

/* Import Customer Split */
proc import datafile="&data_dir/03_POPULATION_AND_SAS_INPUTS/NPA_CUSTOMER_SPLIT.csv"
    out=work.NPA_CUSTOMER_SPLIT dbms=csv replace;
    getnames=yes;
    guessingrows=max;
run;

/* Import Future Outcome (Target for Labelled Development Customers only) */
proc import datafile="&data_dir/02_FUTURE_SIMULATION_AND_TARGET/future_outcome.csv"
    out=work.future_outcome dbms=csv replace;
    getnames=yes;
    guessingrows=max;
run;

/*--------------------------------------------------------------------------
  2. DATA QUALITY & INTEGRITY AUDIT IN SAS
--------------------------------------------------------------------------*/

/* Check 1: Record Counts */
proc sql noprint;
    select count(*) into :cm_count from work.customer_master;
    select count(*) into :la_count from work.loan_account;
    select count(*) into :eh_count from work.emi_history;
    select count(*) into :ph_count from work.payment_history;
    select count(*) into :cb_count from work.credit_bureau;
    select count(*) into :th_count from work.transaction_history;
    select count(*) into :ccd_count from work.customer_company_details;
    select count(*) into :split_count from work.NPA_CUSTOMER_SPLIT;
    select count(*) into :fo_count from work.future_outcome;
quit;

%put NOTE: ========================================================;
%put NOTE: SAS IMPORT RECORD COUNTS:;
%put NOTE: customer_master          = &cm_count (Expected: 12,000);
%put NOTE: loan_account             = &la_count (Expected: 12,000);
%put NOTE: emi_history              = &eh_count (Expected: 144,000);
%put NOTE: payment_history          = &ph_count (Expected: 144,000);
%put NOTE: credit_bureau            = &cb_count (Expected: 12,000);
%put NOTE: transaction_history      = &th_count (Expected: 144,000);
%put NOTE: customer_company_details = &ccd_count (Expected: 12,000);
%put NOTE: NPA_CUSTOMER_SPLIT       = &split_count (Expected: 12,000);
%put NOTE: future_outcome           = &fo_count (Expected: 10,000);
%put NOTE: ========================================================;

/* Check 2: Current Loan Strict Performing Status */
proc sql;
    select count(*) as unpaid_current_emi
    from work.emi_history
    where emi_paid ne emi_due;

    select count(*) as nonzero_current_dpd
    from work.emi_history
    where days_past_due ne 0;

    select count(*) as nonzero_current_npa
    from work.emi_history
    where npa_indicator ne 0;

    select count(*) as current_delays_or_bounces
    from work.payment_history
    where payment_delay ne 0 or bounce_flag ne 0 or late_payment_flag ne 0;

    select count(*) as current_bureau_derogatory
    from work.credit_bureau
    where overdue_accounts ne 0 or bureau_dpd ne 0 or writeoff_accounts ne 0;

    select count(*) as low_loan_age
    from work.loan_account
    where loan_age_months < 12;
quit;

/* Check 3: Population Disjointness & Scoring Target Isolation */
proc sql;
    /* Verify scoring population has zero records in future_outcome */
    select count(*) as scoring_target_leakage
    from work.NPA_CUSTOMER_SPLIT as s
    inner join work.future_outcome as f
        on s.customer_id = f.customer_id
    where s.population_role = 'SCORING';

    /* Verify target rate in development population */
    select sum(npa_flag) as positive_events,
           count(*) as total_labelled,
           mean(npa_flag)*100 as positive_rate_pct
    from work.future_outcome;
quit;

%put NOTE: npa_import_and_qa.sas completed successfully.;


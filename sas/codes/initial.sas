/** (c) Karol Przanowski */
/* kprzan@sgh.waw.pl */

options mprint;
options nomprint;

/*all table of codes*/

/*
SET THIS IN THE MAIN PYTHON FILE via sas.sysput BEFORE EXECUTING THIS FILE
%let dir=C:\Projects\rl-debt-collection\sas;
*/
libname data "&dir.data" compress=yes;

%let percent_dec=1.1;
%let n_terms=3;

%let n_terms_vars=2;

%let percent_repeat=0.4;


proc datasets lib=data nolist kill;
quit;

%include "&dir.codes\coeficients_risk_response.sas" / source2;
%include "&dir.codes\dictionaries.sas" / source2;
%include "&dir.codes\clients_code.sas" / source2;
%include "&dir.codes\abt_behavioral_columns.sas" / source2;
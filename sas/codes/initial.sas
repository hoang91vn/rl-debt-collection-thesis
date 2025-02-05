/** (c) Karol Przanowski */
/* kprzan@sgh.waw.pl */

options mprint;
options nomprint;

/*all table of codes*/
%let dir=C:\Projects\bt\DebtCollection\;
libname data "&dir.data" compress=yes;

%let seed=1;

/*%let n_day=5;*/
%let n_day=40;
/*%let n_day=80;*/

%let percent_dec=1.1;
%let n_terms=3;

%let n_terms_vars=2;

%let s_date='01jan2000'd;
/*%let s_date='01jan2002'd;*/
%let e_date='31jan2005'd;

%let percent_repeat=0.4;


proc datasets lib=data nolist kill;
quit;

%include "&dir.codes\coeficients_risk_response.sas" / source2;
%include "&dir.codes\dictionaries.sas" / source2;
%include "&dir.codes\clients_code.sas" / source2;
%include "&dir.codes\abt_behavioral_columns.sas" / source2;
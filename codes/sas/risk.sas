/* (c) Karol Przanowski */
/* kprzan@sgh.waw.pl */

/*%let dimention=year;*/
%let dimention=period;

%let tar1=default3;
%let tar2=default6;
%let tar3=default9;
%let tar4=default12;
%let il_t=4;

%macro do_m;
	%do i=1 %to &il_t;
		&&tar&i %str( )
	%end;
%mend;
%let risk_m=%do_m;
%put &risk_m;



%macro risk(type);
data &type(compress=yes);
set data.abt_&type;
array r(&il_t) &risk_m;
do i=1 to &il_t;
if r(i) in (.i,.d) then r(i)=0;
end;
quarter=compress(put(input(period,yymmn6.),yyq10.));
year=compress(put(input(period,yymmn6.),year4.));
outstanding=app_loan_amount*(app_n_installments-act_paid_installments)/app_n_installments;
credit_limit=app_loan_amount;
keep period year quarter outstanding credit_limit default:;
run;
proc means data=&type noprint nway;
class &dimention;
var &risk_m;
output out=data.&type._risk(drop=_type_ rename=(_freq_=n))
mean(&risk_m)=&risk_m;
format &risk_m nlpct12.2;
run;



proc format;
picture procent (round)
low- -0.005='00.000.000.009,99%'
(decsep=',' 
dig3sep='.'
fill=' '
prefix='-')
-0.005-high='00.000.000.009,99%'
(decsep=',' 
dig3sep='.'
fill=' ')
;
run;

ods listing close;
goptions reset=all device=activex;
ods html path="&dir.reports\"
body="risk_&type..html" style=statistical;

symbol1 i=join c=red line=1 v=dot h=0.5 w=2;
symbol2 i=join c=green line=1 v=dot h=0.5 w=2;
symbol3 i=join c=blue line=1  v=dot h=0.5 w=2;
symbol4 i=join c=black line=1 v=dot h=0.5 w=2;


/*title "Production of &type risk";*/
/*proc gplot data=data.&type._risk;*/
/*plot &dimention*n;*/
/*label n='Production';*/
/*run;*/
/*quit;*/

/*title "Evaluation of &type risk";*/
/*proc gplot data=data.&type._risk;*/
/*plot &dimention**/
/*(&risk_m) */
/*/ overlay legend;*/
/*run;*/
/*quit;*/

proc tabulate data=data.&type._risk;
class &dimention;
var n &risk_m;
table &dimention='', n='N'*sum=''*f=12.
(&risk_m)*sum=''*f=nlpct12.2;
run;

ods html close;
goptions reset=all device=win;
ods listing;
%mend;

%risk(app);
%risk(beh);
%risk(col);
%risk(col_enter);

/* (c) Karol Przanowski */
/* kprzan@sgh.waw.pl */

/*%let dimention=year;*/
%let dimention=period;



proc sort data=data.Transactions(keep=aid period due_installments)
out=data.mig(rename=(due_installments=to));
by aid period;
run;
data data.mig;
set data.mig;
by aid;
from=lag(to);
quarter=compress(put(input(period,yymmn6.),yyq10.));
year=compress(put(input(period,yymmn6.),year4.));
if first.aid then from=.;
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
proc tabulate data=data.mig out=flow;
class &dimention from to;
table &dimention, from='', to='To'*rowpctn=''*f=procent. / box='From';
run;
ods listing;
data data.flow;
set flow;
Flow=put(from,z2.)||'-'||put(to,z2.);
percent=PctN_110/100;
keep &dimention flow percent;
format percent nlpct12.2;
where to=from+1;
run;

ods listing close;
ods html path="&dir.reports\"
body='migration.html' style=statistical;
title 'Migration matrix on all data';
proc tabulate data=data.mig;
class from to;
table from='', to='To'*rowpctn=''*f=procent. / box='From';
run;
proc tabulate data=data.mig;
class from to;
table from='', to='To'*n=''*f=10. / box='From';
run;
ods html close;
ods listing;


ods listing close;
ods html path="&dir.reports\"
body='flow_rates.html' style=statistical;
goptions reset=all device=activex;
title 'Flow rates on all data';
symbol1 i=join c=red line=1 v=dot h=0.5 w=2;
symbol2 i=join c=green line=1 v=dot h=0.5 w=2;
symbol3 i=join c=blue line=1  v=dot h=0.5 w=2;
symbol4 i=join c=black line=1 v=dot h=0.5 w=2;
symbol5 i=join c=yellow line=1 v=dot h=0.5 w=2;
symbol6 i=join c=cyan line=1 v=dot h=0.5 w=2;
symbol7 i=join c=brown line=1 v=dot h=0.5 w=2;

symbol8 i=join c=red line=2 v=dot h=0.5 w=2;
symbol9 i=join c=red line=3 v=dot h=0.5 w=2;
symbol10 i=join c=red line=4 v=dot h=0.5 w=2;
/*proc gplot data=data.flow;*/
/*plot &dimention*percent=flow / overlay;*/
/*run;*/
/*quit;*/
proc sort data=data.flow;
by flow &dimention;
run;
proc tabulate data=data.flow;
class flow &dimention;
var percent;
table &dimention='', flow='Flow'*percent=''*sum=''*f=nlpct12.2;
run;
ods html close;
goptions reset=all device=win;
ods listing;


proc delete data=data.mig;
run;

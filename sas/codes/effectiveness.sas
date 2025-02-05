/* (c) Karol Przanowski */
/* kprzan@sgh.waw.pl */


proc sql;
create table aid_list as
select distinct aid, period from data.Collection_actions;
quit;
proc sql;
create table trans as
select * from data.transactions
where aid in (select distinct aid from aid_list)
order by aid,period;
quit;
data trans2;
set trans;
by aid;
lag=lag(paid_installments);
if first.aid then lag=0;
if paid_installments>lag then paid=1; else paid=0;
keep aid period paid;
run;
proc sort data=data.collection_actions out=actions;
by aid period action_nr;
run;
data sequences;
retain seg 0;
set actions;
by aid period;
if first.period then seg=0;
seg=seg+(10**(action_nr-1))*action;
keep aid period seg;
run;
proc sort data=sequences;
by aid period;
run;
proc sort data=trans2;
by aid period;
run;
data test;
merge trans2 sequences(in=z);
by aid period;
if z;
run;
proc means data=test nway noprint;
class seg;
var paid;
output out=stat_paid mean(paid)=effectiveness;
format effectiveness percent12.2;
run;
proc sort data=stat_paid;
by descending effectiveness;
run;
proc sql;
create table stat_used as
/*select * from stat_paid where seg in (321,322,332,221,334,22,21,31,4321,4332,4311);*/
select * from stat_paid where seg in (321,322,332,221,334,22,21,31,1,2);
quit;

proc sort data=test;
by aid period;
run;
proc sort data=data.abt_col(keep=aid period default:) out=col;
by aid period;
run;
data test_def;
merge test(in=z) col;
by aid period;
if z;
run;
proc means data=test_def nway noprint;
class seg;
var default:;
output out=def_paid mean()=;
format default: percent12.2;
run;
proc sort data=def_paid;
by default12;
run;
proc sql;
create table def_paid_used as
/*select * from stat_paid where seg in (321,322,332,221,334,22,21,31,4321,4332,4311);*/
select * from def_paid where seg in (321,322,332,221,334,22,21,31,1,2);
quit;



ods listing close;
ods html path="&dir.reports\"
body='effectiveness.html' style=statistical;
title 'Effectiveness of debt collection actions';
proc print data=stat_paid;
run;
proc print data=def_paid;
run;

title 'Effectiveness of prefered axtions by a debtor';
proc print data=stat_used;
run;
proc print data=def_paid_used;
run;

ods html close;
ods listing;



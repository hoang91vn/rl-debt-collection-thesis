/* (c) Karol Przanowski */
/* kprzan@sgh.waw.pl */



/*default calculation*/
%macro add_def(period);
proc sql;
create table data.due as
select aid,period,status,due_installments from data.transactions
where aid in (select aid from data.abt_&period)
and period>"&period"
order by aid,period;
quit;

data data.def;
retain n max default3 default6 default9 default12;
set data.due;
by aid;
if first.aid then do;
	n=0; max=0;
	default3=.; default6=.; default9=.; default12=.; 
end;
n+1;
max=max(max,due_installments);
if n=3 then do;
	default3=.i;
	if max<=1 then default3=0;
	if max>2 then default3=1;
end;
if n=6 then do;
	default6=.i;
	if max<=1 then default6=0;
	if max>3 then default6=1;
end;
if n=9 then do;
	default9=.i;
	if max<=1 then default9=0;
	if max>3 then default9=1;
end;
if n=12 then do;
	default12=.i;
	if max<=1 then default12=0;
	if max>3 then default12=1;
end;
if last.aid then do;
	if status ne 'A' then do;
		d=.;
		if status='C' then d=0;
		if status='B' then d=1;
		if n<3 then default3=d;
		if n<6 then default6=d;
		if n<9 then default9=d;
		if n<12 then default12=d;
	end;
	output;
end;
keep aid default3 default6 default9 default12;
run;
proc sort data=data.abt_&period;
by aid;
run;
proc sort data=data.def;
by aid;
run;
data data.abt_&period;
merge data.abt_&period(in=z) data.def;
by aid;
if z;
run;
%mend;

proc sql noprint;
select 
'%add_def('||trim(substr(memname,5))||')'
into :periods separated by ';'
from dictionary.tables where libname='DATA'
and (memname like 'ABT_1%' or memname like 'ABT_2%');
quit;
&periods;


proc sql noprint;
select 
'data.'||memname
into :periods separated by ' '
from dictionary.tables where libname='DATA'
and (memname like 'ABT_1%' or memname like 'ABT_2%');
quit;



data data.abt_app data.abt_beh data.abt_col_enter data.abt_col;
set
&periods;

app_char_branch=        put(app_nom_branch,branch.);
app_char_gender=        put(app_nom_gender,gender.);
app_char_job_code=      put(app_nom_job_code,jobc.);
app_char_marital_status=put(app_nom_marital_status,martials.);
app_char_city=          put(app_nom_city,city.);
app_char_home_status=   put(app_nom_home_status,homes.);
app_char_cars=          put(app_nom_cars,cars.);

/*application*/
if act_days=15 and act_paid_installments=0 and act_due=0
	and period=fin_period then output data.abt_app;
/*behavioral*/
if not missing(agr3_Max_Due) and act_due=0
 	then output data.abt_beh;
/*collection entrance*/
if act_due=1
 	then output data.abt_col_enter;
/*collection*/
if coll_status>=2
 	then output data.abt_col;
drop
app_nom_branch
app_nom_gender
app_nom_job_code
app_nom_marital_status
app_nom_city
app_nom_home_status
app_nom_cars
;
run;
proc datasets lib=data nolist;
modify abt_app;
index create period;
index create aid;
run;
modify abt_beh;
index create period;
index create aid;
run;
modify abt_col;
index create period;
index create aid;
run;
modify abt_col_enter;
index create period;
index create aid;
run;
quit;

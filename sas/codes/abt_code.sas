/** (c) Karol Przanowski */
/* kprzan@sgh.waw.pl */


/*abt calculation*/
/*migration matrix*/
data data.mat;
infile cards dlm=' ' firstobs=2;
input from to0-to12;
cards;
bucket  0     1     2     3     4     5     6     7     8     9    10    11    12
0   0.850 0.150 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000
1   0.250 0.600 0.150 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000
2   0.040 0.220 0.200 0.540 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000
3   0.005 0.020 0.081 0.102 0.792 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000
4   0.000 0.000 0.010 0.080 0.090 0.820 0.000 0.000 0.000 0.000 0.000 0.000 0.000
5   0.000 0.000 0.000 0.010 0.020 0.030 0.940 0.000 0.000 0.000 0.000 0.000 0.000
6   0.000 0.000 0.000 0.000 0.010 0.020 0.030 0.940 0.000 0.000 0.000 0.000 0.000
7   0.000 0.000 0.000 0.000 0.000 0.010 0.020 0.030 0.940 0.000 0.000 0.000 0.000
8   0.000 0.000 0.000 0.000 0.000 0.000 0.010 0.020 0.030 0.940 0.000 0.000 0.000
9   0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.010 0.020 0.030 0.940 0.000 0.000
10  0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.010 0.020 0.030 0.940 0.000
11  0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.010 0.020 0.030 0.940
;
run;

data data.mat_positive;
infile cards dlm=' ' firstobs=2;
input from to0-to12;
cards;
bucket  0     1     2     3     4     5     6     7     8     9    10    11    12
0   0.800 0.200 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000
1   0.250 0.850 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000
2   0.050 0.750 0.200 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000
3   0.005 0.025 0.080 0.890 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000
4   0.000 0.000 0.012 0.088 0.900 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000
5   0.000 0.000 0.000 0.010 0.090 0.900 0.000 0.000 0.000 0.000 0.000 0.000 0.000
6   0.000 0.000 0.000 0.000 0.010 0.090 0.900 0.000 0.000 0.000 0.000 0.000 0.000
7   0.000 0.000 0.000 0.000 0.000 0.010 0.090 0.900 0.000 0.000 0.000 0.000 0.000
8   0.000 0.000 0.000 0.000 0.000 0.000 0.010 0.090 0.900 0.000 0.000 0.000 0.000
9   0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.010 0.090 0.900 0.000 0.000 0.000
10  0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.010 0.090 0.900 0.000 0.000
11  0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.010 0.090 0.900 0.000
;
run;


data data.transactions;
length cid $10 aid $16 period fin_period $6 status $1
coll_status due_installments paid_installments pay_days 8;
delete;
run;
proc datasets lib=data nolist;
modify transactions;
index delete _all_;
index create period;
index create status;
index create coll_status;
index create comp=(status period);
index create comp1=(coll_status period);
index create comp2=(aid period);
index create comp3=(cid period);
index create cid;
index create aid;
quit;


data data.collection_actions;
length cid $10 aid $16 period $6 action_nr action coll_status 8;
delete;
run;
proc datasets lib=data nolist;
modify collection_actions;
index delete _all_;
index create period;
index create coll_status;
index create comp1=(coll_status period);
index create comp2=(aid period);
index create comp3=(cid period);
index create cid;
index create aid;
quit;

/*account allocation*/
%macro allocate(period);
data tmp;
run;
data tmp;
length cid $10 aid $16 period fin_period $6 status $1
coll_status due_installments paid_installments pay_days 8;
set data.production;
fin_period=period;
due_installments=0;
paid_installments=0;
pay_days=0;
status='A';
coll_status=1;
keep
cid aid period fin_period status coll_status
due_installments paid_installments pay_days;
where period="&period";
run;
proc append base=data.transactions data=tmp;
run;
%mend allocate;




/*abt calculation*/
%macro movemonth1(period,period1);
%allocate(&period);


proc sql;
create table data.abt_tmp as
select * from data.Transactions
where aid in
(select aid from data.Transactions
where status='A' and period="&period1") and period<="&period1"
;
quit;

data data.abt_tmp;
set data.abt_tmp;
set data.Production(drop=app_date period) key=aid / unique;
if _iorc_ ne 0 then _error_=0;
run;

data data.abt_p1;
set data.abt_tmp;
/*characteristics*/
act_days=pay_days+15;
act_paid_installments=paid_installments;
act_utl=paid_installments/n_installments;
act_dueutl=due_installments/n_installments;
act_due=due_installments;
act_age=int(yrdif(data_of_birth,input(period,yymmn6.),'ACT/ACT'));
act_cc=(installment+spendings)/income;
act_dueinc=due_installments*installment/income;
act_loaninc=loan_amount/income;
app_income=income;
app_loan_amount=loan_amount;
app_n_installments=n_installments;
act_seniority=intck('month',input(fin_period,yymmn6.),input(period,yymmn6.))+1;

app_nom_branch=branch;
app_nom_gender=gender;
app_nom_job_code=job_code;
app_number_of_children=number_of_children;
app_nom_marital_status=marital_status;
app_nom_city=city;
app_nom_home_status=home_status;
app_nom_cars=cars;
app_spendings=spendings;

/*characteristics*/
where period="&period1";
keep cid aid act: app: fin_period status coll_status period;
run;

/*preparation of data*/
proc sort data=data.abt_tmp;
by aid period;
run;
data data.abt_p2;
set data.abt_tmp;
/*characteristics*/
days=pay_days+15;
due=due_installments;
/*characteristics*/
keep period cid aid days due;
run;

proc transpose data=data.abt_p2 prefix=days_
out=data.abt_days(drop=_name_ _lebel_);
var days;
id period;
by aid;
run;
proc transpose data=data.abt_p2 prefix=due_
out=data.abt_due(drop=_name_ _lebel_);
var due;
id period;
by aid;
run;

/*customer level*/
proc sql;
create table data.abt_tmp_cus as
select * from data.Transactions
where cid in
(select distinct cid from data.Transactions
where status='A' and period="&period1") and period<="&period1"
;
quit;
data data.abt_tmp_cus;
set data.abt_tmp_cus;
set data.Production(drop=app_date period) key=aid / unique;
if _iorc_ ne 0 then _error_=0;
run;
data data.abt_p2c;
set data.abt_tmp_cus;
/*characteristics*/
days=pay_days+15;
due=due_installments;
/*characteristics*/
keep period cid aid days due;
run;
proc means data=data.abt_p2c nway noprint;
class cid period;
var days due;
output out=data.abt_p2_cus(drop=_type_ _freq_)
max(days due)= cmax_days cmax_due;
run;
proc sort data=data.abt_p2;
by cid period;
run;
proc sort data=data.abt_p2_cus;
by cid period;
run;
proc sort data=data.abt_p2 out=data.abt_p3_rel(keep=cid aid) nodupkey;
by aid;
run;
proc transpose data=data.abt_p2_cus prefix=CMax_due_
out=data.abt_CMax_due(drop=_name_ _lebel_);
var CMax_due;
id period;
by cid;
run;
proc transpose data=data.abt_p2_cus prefix=CMax_days_
out=data.abt_CMax_days(drop=_name_ _lebel_);
var CMax_days;
id period;
by cid;
run;

proc means data=data.abt_tmp_cus nway noprint;
class cid;
var paid_installments n_installments
	due_installments income installment spendings;
output out=data.abt_tmp_cus_agr(drop=_type_ _freq_)
sum(paid_installments n_installments due_installments installment spendings)=
paid_installments n_installments due_installments installment spendings
max(income)=income n(income)=act_cus_n_loans_act;
where period="&period1";
run;
data data.abt_tmp_cus_agr;
set data.abt_tmp_cus_agr;
act_cus_utl=paid_installments/n_installments;
act_cus_dueutl=due_installments/n_installments;
act_cus_cc=(installment+spendings)/income;
keep cid act:;
run;
proc sort data=data.abt_tmp_cus_agr;
by cid;
run;

proc sort data=data.abt_tmp_cus out=data.loan_number;
by cid fin_period aid;
where period="&period1";
run;
data data.loan_number;
set data.loan_number;
by cid;
if first.cid then act_cus_loan_number=0;
act_cus_loan_number+1;
keep aid act_cus_loan_number;
run;
proc sort data=data.loan_number;
by aid;
run;

proc sql;
create table data.abt_cus_hist as
select cid,
max(intck('month',input(fin_period,yymmn6.),input("&period1",yymmn6.))+1)
as act_cus_seniority,
count(distinct aid) as act_cus_n_loans_hist,
sum((status='C')) as act_cus_n_statC,
sum((status='B')) as act_cus_n_statB
from data.abt_tmp_cus
group by 1
order by 1;
quit;

proc sort data=data.abt_p1;
by cid;
run;
data data.abt_p1;
merge data.abt_p1(in=z) data.abt_cus_hist data.abt_tmp_cus_agr;
by cid;
if z;
run;
/*customer level*/

proc sort data=data.abt_due;
by aid;
run;
proc sort data=data.abt_days;
by aid;
run;
proc sort data=data.abt_CMax_due;
by cid;
run;
proc sort data=data.abt_CMax_days;
by cid;
run;
data data.abt_dd0;
merge data.abt_days data.abt_due data.Abt_p3_rel;
by aid;
run;
proc sort data=data.abt_dd0;
by cid;
run;
data data.abt_dd;
merge data.abt_dd0(in=z) data.abt_CMax_days data.abt_CMax_due;
by cid;
if z;
run;

/*begining of the program*/
/*options mprint;*/
%let data_wej=data.abt_dd;
%let data_wyj=data.tmp_abt;
%let id_account=aid;
%make_abt(&period1);

proc sort data=data.abt_p1;
by aid;
run;
proc sort data=data.tmp_abt;
by aid;
run;
data data.abt_&period1;
merge data.abt_p1(in=z) data.tmp_abt data.loan_number;
by aid;
if z;
run;

/*coll scoring calculation*/
data data.tmp_coll;
set data.abt_&period1;
run;
%let zbior=data.tmp_coll;
%include "&dir.codes\coll_scoring_code.sas" / source2;
proc sort data=data.tmp_coll_score;
by coll_status act_due scorecard_points;
run;
proc rank data=data.tmp_coll_score out=data.tmp_coll_score_rank groups=2;
by coll_status act_due;
var scorecard_points;
ranks coll_rank;
run;
data data.abt_&period1;
set data.tmp_coll_score_rank;
if coll_status=1 then do;
	scorecard_points=.;
	coll_rank=.;
end;
run;
/*coll scoring calculation*/


proc standard data=data.abt_&period1 out=data.abt_score
mean=0 std=1 replace;
run;

data data.abt_score_c;
set data.abt_score;
scorem=sum(
1*app_income,
1*app_nom_branch,
1*app_nom_gender,
2*app_nom_job_code,
1*app_number_of_children,
1*app_nom_marital_status,
1*app_nom_city,
1*app_nom_home_status,
1*app_nom_cars
);

score=sum(
-1*act_cus_utl,
-1*act_cus_dueutl,
-1*act_cus_cc,
-1*act_cus_n_loans_act,
 3*act_cus_seniority,
-5*act_cus_loan_number,
 5*(act_cus_loan_number=1),
 6*act_cus_n_statC,
-3*act_cus_n_statB,

 1*app_nom_branch,
 3*app_nom_gender,
 6*app_nom_job_code,
-3*(app_nom_job_code=4 and app_nom_marital_status in (2,3)
	and app_nom_gender=2),
 2*(app_nom_job_code=4 and app_nom_marital_status in (2,3)
	and app_nom_gender=1),
 6*app_number_of_children,
 3*app_nom_marital_status,
 1*app_nom_city,
 1*app_nom_home_status,
 1*app_nom_cars,
-1*app_spendings,
-5*act_days ,
-4*act_utl ,
-6*act_dueutl ,
-2*act_due ,
 4*act_age ,
-2*act_cc ,
-1*act_dueinc ,
-2*act_loaninc ,
 2*app_income ,
-1*app_loan_amount ,
-4*app_n_installments ,

-2*agr3_Mean_Due ,
-3*ags3_Mean_Days ,

-3*agr6_Mean_Due ,
-3*ags6_Mean_Days ,

-2*agr9_Mean_Due ,
-3*ags9_Mean_Days ,

-2*agr12_Mean_Due ,
-3*ags12_Mean_Days,

-3*ags3_Max_CMax_Due,
-2*ags12_Max_CMax_Due,
-2*ags9_Max_CMax_Days,
-1*act_n_cus_arrears,
-2*ags12_Max_CMax_Due,
 5*(ags12_Max_CMax_Due=0)

)
;
keep aid score scorem;
run;

proc standard data=data.abt_score_c out=data.abt_score
mean=0 std=1;
run;

data data.abt_score;
set data.abt_score;
score=sum(score,rannor(&seed)/2);
scorem=sum(scorem,rannor(&seed)/2);
run;

proc sort data=data.abt_score;
by aid;
run;
proc sort data=data.abt_&period1;
by aid;
run;
data data.abt_score;
merge data.abt_&period1 data.abt_score;
by aid;
run;


proc means data=data.abt_score noprint nway;
class act_due;
var score;
output out=stat(drop=_freq_ _type_) n()=n;
run;
proc means data=data.abt_score noprint nway;
class coll_status;
var score;
output out=stat_coll(drop=_freq_ _type_) n()=n;
run;

data collection_actions;
length cid $10 aid $16 period $6 action_nr action coll_status 8;
delete;
run;
%mend movemonth1;

%macro vanilla_actions();
/*running actions*/
data collection_actions;
length cid $10 aid $16 period $6 action_nr action coll_status 8;
set data.abt_score;
if coll_status ne 1 and coll_status ne 7 and coll_status ne 8 then do;
	num_actions=int(ranuni(&seed)*3+1);
	do action_nr=1 to num_actions;
		action=int(ranuni(&seed)*3+1);
		output;
	end;
end;
keep cid aid period action_nr action coll_status;
run;
/*running actions*/
%mend vanilla_actions;

%macro movemonth2(period,period1);
/*debtor behaviour*/
proc sort data=collection_actions out=actions;
by aid action_nr;
run;
data sequences;
retain seg 0;
set actions;
by aid;
if first.aid then seg=0;
seg=seg+(10**(action_nr-1))*action;
if last.aid;
positive_reaction=0;
if coll_status=2 and seg in (321,322,332,221,334,22,21,31,1,2) then positive_reaction=1;
if coll_status=3 and seg in (321,322,332,221,334,22,21,31,1,2) then positive_reaction=1;
if coll_status=4 and seg in (321,322,332,221,334,22,21,31,1,2) then positive_reaction=1;
if coll_status=5 and seg in (321,322,332,221,334,22,21,31,1,2) then positive_reaction=1;
if coll_status=6 and seg in (321,322,332,221,334,22,21,31,1,2) then positive_reaction=1;

/*in future add some share*/
/*if ranuni(&seed)<0.5 then positive_reaction=positive_reaction; else positive_reaction=0;*/
keep aid seg positive_reaction;
run;
/*debtor behaviour*/



proc sort data=data.abt_score;
by aid;
run;
proc sort data=sequences;
by aid;
run;
data data.abt_score;
merge data.abt_score sequences;
by aid;
run;
proc sort data=data.abt_score;
by act_due descending score;
run;


data data.abt_class;
array mat(0:11,0:12);
array mat_positive(0:11,0:12);
array mat_b(0:11,0:12);
array mat_temp(0:12) to0-to12;
array mat_n(0:12);
array coef_pr(0:500);

do i=1 to nobcof;
	set data.coeficients(obs=500) nobs=nobcof;
	coef_pr(i-1)=pr_risk;
end;


/*reading matrix*/
do fro=0 to 11;
	set data.mat;
	do to=0 to 12;
		mat_b(fro,to)=mat_temp(to);
	end;
end;
do fro=0 to 11;
	set data.mat_positive;
	do to=0 to 12;
		mat_positive(fro,to)=mat_temp(to);
	end;
end;
/*put mat(1,1)=;*/

do i=1 to nob;
	set stat nobs=nob;
	mat_n(act_due)=n;
end;
/*put mat_n(0)=;*/

do obs=1 to nobs;
	set data.abt_score nobs=nobs;
	by act_due;
	period="&period";

	/*base matrix*/
	do fro=0 to 11;
		do to=0 to 12;
			mat(fro,to)=mat_b(fro,to);
		end;
	end;

/*modification of migration matrix*/
/*	if scorem>0 then do;*/
/*		j=intck('month',&s_date,input(period,yymmn6.));*/
/*		pr=coef_pr(j);*/
/*		do from=0 to 11;*/
/*			d=0;*/
/*			do i=0 to from;*/
/*				d=d+pr*mat(from,i);*/
/*				mat(from,i)=mat(from,i)*(1-pr);*/
/*			end;*/
/*			mat(from,from+1)=mat(from,from+1)+d;*/
/*		end;*/
/*	end;*/
/*modification of migration matrix*/


	if first.act_due then ob=0;
	ob=ob+1;
	if 0<=act_due<12 then do;
		pr=0;
		pr_positive=0;
		do to=0 to 12;
			if (ob>pr*mat_n(act_due) and positive_reaction ne 1) or (ob>pr_positive*mat_n(act_due) and positive_reaction=1) then do;
				/*movement from act_due to to*/
				if act_due<to then do;
					/*no payment*/
					paid_installments=act_paid_installments;
					due_installments=to;
					pay_days=.;
					if coll_status=1 or coll_status=7 and due_installments=1 then coll_status=2;
					if coll_status=2 and due_installments=4 then coll_status=3;
					if coll_status=3 and due_installments=5 then coll_status=4;
					if coll_status=4 and due_installments=7 then coll_status=5;
					if coll_status=5 and due_installments=10 then coll_status=6;
				end; else do;
					/*payment*/
					paid_installments=act_paid_installments+act_due-to+1;
					due_installments=to;
					if paid_installments>app_n_installments then
							paid_installments=app_n_installments;
					if act_due<2 then pay_days=-int(15*(abs(rannor(1))/4));
					else pay_days=int(15*(rannor(1)/4));
				end;
			end;
			pr=pr+mat(act_due,to);
			pr_positive=pr_positive+mat_positive(act_due,to);
		end;
		if coll_status>1 and due_installments=0 then coll_status=7;
		if paid_installments=app_n_installments then status='C';
	end;
	if act_due=12 then do;
		/*end*/
		due_installments=12;
		paid_installments=act_paid_installments;
		pay_days=.;
		status='B';
		coll_status=8;
	end;
	output;
end;
keep
cid aid period fin_period status coll_status
due_installments paid_installments pay_days;
run;

proc append base=data.transactions data=data.abt_class;
run;

proc append base=data.Collection_actions data=Collection_actions;
run;

%mend movemonth2;

%macro final;
proc sql noprint;
select period into :prod_periods separated by '#'
from data.Production_stat;
quit;
%let n_prod_periods=&sqlobs;
%put &n_prod_periods***&prod_periods;

%let fperiod=%scan(&prod_periods,1,#);
%put &fperiod;
%allocate(&fperiod);

%do fi=2 %to &n_prod_periods;
	%let fiperiod=%scan(&prod_periods,&fi,#);
	%let fiperiod1=%scan(&prod_periods,%eval(&fi-1),#);
	%movemonth1(&fiperiod,&fiperiod1);
	%vanilla_actions;
	%movemonth2(&fiperiod,&fiperiod1);
%end;
%mend final;
/*
%final;
*/


/* (c) Karol Przanowski */
/* kprzan@sgh.waw.pl */


%macro make_abt(period);

%let max_length=12;

data periods;
periodp=input("&period",yymmn6.);
do i=0 to &max_length-1;
period=put(intnx('month',periodp,-i,'end'),yymmn6.);
output;
end;
keep period;
run;

proc sql noprint;
select period
into :periods separated by ' '
from periods order by 1;
quit;
%let n_periods=&max_length;
%put &n_periods;
%put &periods;


%let first_period=%scan(&periods,1,%str( ));
%put &first_period;

data _null_;
index=intck('month',input("&first_period",yymmn6.),input("&period",yymmn6.))+1;
call symput('index',put(index,best12.-L));
run;
%put &index;

%let var1=Due;
%let var2=Days;
%let var3=CMax_Days;
%let var4=CMax_Due;
%let n_var_agr=4;

%let sagr1=Mean;
%let sagr2=Max;
%let sagr3=Min;
%let n_sagr=3;

%let lengths=3 6 9 12;
%let n_lengths=4;

data &data_wyj;
array tx(&max_length);
array ty(&max_length);

set &data_wej;

%do len=1 %to &n_lengths;
%let length=%scan(&lengths,&len,%str( ));
%let first_index=%eval(&index-&length+1);
%if &first_index<1 %then %let first_index=1;
	%do v=1 %to &n_var_agr;
		%do a=1 %to &n_sagr;
			agr&length._&&sagr&a.._&&var&v=&&sagr&a(
			%do i=&first_index %to &index;
				%let p=%scan(&periods,&i,%str( ));
				&&var&v.._&p ,
				%end;
			.);
			nmiss=nmiss(
			%do i=&first_index %to &index;
				%let p=%scan(&periods,&i,%str( ));
				&&var&v.._&p ,
				%end;
			.);
			ags&length._&&sagr&a.._&&var&v=agr&length._&&sagr&a.._&&var&v;
			if nmiss>1 then agr&length._&&sagr&a.._&&var&v=.m;
		%end;
	%end;
%end;

act_n_arrears=sum(
			%do i=&first_index %to &index;
				%let p=%scan(&periods,&i,%str( ));
				(due_&p >= 1) ,
				%end;
			.);

act_n_arrears_days=sum(
			%do i=&first_index %to &index;
				%let p=%scan(&periods,&i,%str( ));
				(days_&p > 15) ,
				%end;
			.);

act_n_good_days=sum(
			%do i=&first_index %to &index;
				%let p=%scan(&periods,&i,%str( ));
				(0 < days_&p < 15) ,
				%end;
			.);

act_n_cus_arrears=sum(
			%do i=&first_index %to &index;
				%let p=%scan(&periods,&i,%str( ));
				(CMax_Due_&p >= 1) ,
				%end;
			.);


if _error_=1 then _error_=0;
keep &id_account agr: act: ags:;
run;

%mend;

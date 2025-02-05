/* (c) Karol Przanowski */
/* kprzan@sgh.waw.pl */



data 
data.clients1(keep=cid data_of_birth gender)
data.production1(keep=
aid cid app_date period data_of_birth installment 
n_installments loan_amount branch)

data.production2(keep=
aid cid app_date period installment n_installments loan_amount branch)

;
length aid $16 cid $10;
n=1;
do app_date=&s_date to &e_date;
	max=&n_day*(1+rannor(&seed)/20);
	if month(app_date)=12 then max=max*&percent_dec;
	period=put(app_date,yymmn6.);

	term=intck('month',&s_date,&e_date)+1;
	j=intck('month',&s_date,input(period,yymmn6.));
	pr=(0.01+(1.5+sin(&n_terms_vars*3.1412*j/term)+rannor(&seed)/5)/8)/0.36;

	do i=1 to max;
		aid='ins'||put(app_date,yymmddn8.)||put(i,z4.)||'1';
		x=int((75-18)*(rannor(&seed)+4)/7 + 10 + 20*ranuni(&seed)+5*pr);
		if x<18 then x=18;
		if x>75 then x=75;
		data_of_birth=int(app_date-x*365.5);
		cid=put(n,z10.);
		gender=(ranuni(&seed)>(0.45+pr/20))+1;
		if gender>2 then gender=2;
		if gender<1 then gender=1;
		installment=int(abs(rannor(&seed))*200+60+50*pr);
		n_installments=12;
		if ranuni(&seed)<(0.3+pr/50) then n_installments=24;
		if ranuni(&seed)<(0.2-pr/50) then n_installments=36;
		loan_amount=n_installments*installment;
		branch=int(ranuni(&seed)*3+1.5+pr/10);
		if branch>4 then branch=4;
		if branch<1 then branch=1;
		output data.production1;
		output data.clients1;
		if ranuni(&seed)<&percent_repeat then do;
			aid='ins'||put(app_date,yymmddn8.)||put(i,z4.)||'2';
			m=int(n*abs(rannor(&seed))/5);
			if m<1 then  m=1;
			if m>n then m=n;
			cid=put(m,z10.);
			installment=int(abs(rannor(&seed))*200+60);
			n_installments=12;
			if ranuni(&seed)<0.3 then n_installments=24;
			if ranuni(&seed)<0.2 then n_installments=36;
			loan_amount=n_installments*installment;
			branch=int(ranuni(&seed)*3+1.5);
			if branch>4 then branch=4;
			if branch<1 then branch=1;
			output data.production2;
		end;
		if ranuni(&seed)<&percent_repeat then do;
			aid='ins'||put(app_date,yymmddn8.)||put(i,z4.)||'3';
			m=int(n*abs(rannor(&seed))/5);
			if m<1 then  m=1;
			if m>n then m=n;
			cid=put(m,z10.);
			installment=int(abs(rannor(&seed))*200+60);
			n_installments=12;
			if ranuni(&seed)<0.3 then n_installments=24;
			if ranuni(&seed)<0.2 then n_installments=36;
			loan_amount=n_installments*installment;
			branch=int(ranuni(&seed)*3+1.5);
			if branch>4 then branch=4;
			if branch<1 then branch=1;
			output data.production2;
		end;
		n=n+1;
	end;
end;
format app_date data_of_birth yymmdd10. 
;
run;

%let income_i_spendings=%str(
income=int((5000-500)*abs(rannor(&seed))/4+500);
if job_code=3 then income=int((7000-1500)*abs(rannor(&seed))/4+1500);
if job_code=4 then income=int((4000-300)*abs(rannor(&seed))/4+300);
if job_code=2 then income=int((17000-3000)*abs(rannor(&seed))/4+3000);
spendings=20*int(income*(abs(rannor(&seed))+home_status+cars-2)/(8*20));
);


data data.clients_all;
set data.clients1;
year_s=year(&s_date);
year_e=year(&e_date);
yearb=year(data_of_birth);
do year=yearb+18 to year_e;
	age=year-yearb;
	if age=18 then do;
		job_code=1+(ranuni(&seed)<0.4)*2;
		number_of_children=0;
		marital_status=1;
		city=int(ranuni(&seed)*3+1.5);
		if city>4 then city=4;
		if city<1 then city=1;
		home_status=int(ranuni(&seed)*2+1.5);
		if home_status>3 then home_status=3;
		if home_status<1 then home_status=1;
		cars=1;
		&income_i_spendings;
	end; else do;
		if marital_status=1 and age<60 and ranuni(&seed)<0.1 then
			marital_status=4;
		if number_of_children<1 and marital_status=4 
			and ranuni(&seed)<0.1 and age<45 then number_of_children=number_of_children+1;
		if number_of_children=1 and marital_status=4 
			and ranuni(&seed)<0.05 and age<45 then number_of_children=number_of_children+1;
		if number_of_children=2 and marital_status=4 
			and ranuni(&seed)<0.01 and age<45 then number_of_children=number_of_children+1;
		if number_of_children>0 and age>45 and ranuni(&seed)<0.1 then 
			number_of_children=number_of_children-1;
		if marital_status=4 and ranuni(&seed)<0.01 then marital_status=2;
		if marital_status=4 and age>60 and ranuni(&seed)<0.1 then marital_status=3;
		
		if (marital_status=4 or age>25) and home_status=1 and ranuni(&seed)<0.7 
			then home_status=2;
		if (marital_status=4 or age>25) and home_status=1 and ranuni(&seed)<0.2 
			then home_status=3;
		if home_status=2 and ranuni(&seed)<0.05 
			then home_status=3;
		if ranuni(&seed)<0.005 then do;
			city=int(ranuni(&seed)*3+1.5);
			if city>4 then city=4;
			if city<1 then city=1;
		end;
		if cars=1 and 20<age<=60 and ranuni(&seed)<0.05 then cars=2; 
		if cars=2 and ranuni(&seed)<0.001 then cars=1; 

		if job_code ne 4 and age>50 and ranuni(&seed)<0.1 then do; 
			job_code=4;
			&income_i_spendings;
		end;
		if job_code ne 4 and age>70 then do;
			job_code=4;
			&income_i_spendings;
		end;
		if job_code=1 and ranuni(&seed)<0.05 then do;
			job_code=3;
			&income_i_spendings;
		end;
		if job_code in (3,1) and ranuni(&seed)<0.01 then do;
			job_code=2;
			&income_i_spendings;
		end;
		if job_code=2 and ranuni(&seed)<0.01 then do;
			job_code=3;
			&income_i_spendings;
		end;
		if job_code in (3,2) and ranuni(&seed)<0.005 then do;
			job_code=1;
			&income_i_spendings;
		end;
	end;
	if year>=year_s then output;	
end;
drop 
year_s year_e yearb;
run;


proc datasets lib=data nolist;
modify Clients_all;
index delete _all_;
index create klucz=(cid year) / unique;
quit;

data data.production1;
set data.production1;
year=year(app_date);
set data.clients_all key=klucz / unique;
if _iorc_ ne 0 then do;
	_error_=0;
	put 'byly b³edy w cid' year= cid=;
end;
if age<100;
run;


data data.production2;
set data.production2;
year=year(app_date);
set data.clients_all key=klucz / unique;
if _iorc_ ne 0 then do;
	_error_=0;
	put 'byly b³edy w cid';
end;
if age<100;
run;



proc means data=data.production1 noprint nway;
class period;
var installment;
output out=data.production1_stat(drop=_freq_ _type_) n(installment)=n;
run;

proc means data=data.production2 noprint nway;
class period;
var installment;
output out=data.production2_stat(drop=_freq_ _type_) n(installment)=n;
run;


data data.production;
set data.production1 data.production2;
run;
proc sort data=data.production;
by app_date aid;
run;
proc datasets lib=data nolist;
modify production;
index delete _all_;
index create period;
index create aid;
index create cid;
quit;


proc means data=data.production noprint nway;
class period;
var installment;
output out=data.production_stat(drop=_freq_ _type_) n(installment)=n;
run;

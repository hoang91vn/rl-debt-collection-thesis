data &zbior._score;
set &zbior;

scorecard_points=sum(
-1*act_cus_utl,
-1*act_cus_cc,
 3*act_cus_seniority,
-5*act_cus_loan_number,
 6*act_cus_n_statC,
-3*act_cus_n_statB,
 4*act_age ,
-2*agr3_Mean_Due ,
-3*agr6_Mean_Due ,
-3*ags3_Max_CMax_Due,
-2*ags12_Max_CMax_Due);

run;

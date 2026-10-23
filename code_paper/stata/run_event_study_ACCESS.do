*------------------------------------------------------------------------------
* MAI event-study regressions: Figures 9 and 10 of the paper
*
*   PAPER EXHIBIT        SECTION BELOW                         FILE (in paper_exhibits)
*   Figure 9, panel a    Regression 1: access x year           fig09a_access_categories.png
*   Figure 9, panel b    Regression 2: population, travel      fig09b_population_travel.png
*   Figure 9, panel c    Regression 3: two-day markets         fig09c_two_day_markets.png
*   Figure 9, panel d    Regression 4: single vs multi-day     fig09d_single_multi_day.png
*   Figure 10, panel a   NTL by access category                fig10a_ntl_access_categories.png
*   Figure 10, panel b   NTL, population and travel time       fig10b_ntl_population_travel.png
*
* Figures go to output_paper/paper_exhibits (the folder every script in the
* repository writes paper exhibits to; see EXHIBITS.md). The regression tables
* behind them (MAI_pooled.xls, NTL_access.xls) go to output_paper/event_study.
* Vertical bars are 90% confidence intervals, t(G-1), G = province clusters.
* (The paper's notes for Figures 9 and 10 say 95 percent; the authors chose 90%.)
*
* Input : event_study_panel.dta (build_event_study_panel.ipynb) and
*         event_study_days_panel.dta (data_build/build_event_study_days_panel.py)
* Earlier specifications that are not in the paper (per-access regressions with
* once-a-week terms and their figures) are in archive/stata/run_event_study_ACCESS_full.do.
*
* ssc install reghdfe,  replace
* ssc install ftools,   replace
* ssc install coefplot, replace
* ssc install outreg2,  replace
*------------------------------------------------------------------------------
clear all
set more off

if c(username) == "wb434633" {
    global root = "C:\Users\wb434633\WBG\Christina Wieser - Afghanistan\Geospatial information\MarketActivityIndex\processed_data"
}
else{
    global root = "C:\Users\wb306348\OneDrive - WBG\Afghanistan\Geospatial information\MarketActivityIndex\processed_data"
}

loc NEW = 1
if `NEW' == 1 {
    use "$root/event_study_panel.dta", clear 
}
else{
    use "$root/event_study_panel_OLD.dta", clear 

    gen log_light_emissions = ln(feb_jun_median_bnr)
    ren feb_jun_median_bnr light_emissions
    ren ndvi_dev ndvi_ag_anom 
    
    set seed 12345
    generate access = runiformint(1, 3)
    ren log_pop ln_pop_30mixed 
    
}



egen market_id   = group(mktID)
egen district_id = group(Pcode_24)

ta Prov_ID, gen(prov_id_dummy)

xtset market_id year

local BASE 2020

*------------------------------------------------------------------------------
* Variables.
*
* The three time-invariant characteristics are centred on their mean across
* markets. Market and year fixed effects absorb their main effects, so centring
* does not change the interaction coefficients; it is kept to mirror the notebook.
*
* Interaction terms are built explicitly (NOT i.year#c.X with year in absorb()),
* which gives one coefficient per year per regressor with 2020 omitted by
* construction, and no collinearity notes.
*------------------------------------------------------------------------------

gen  low_periodicity = (once_a_week == 1)
recast double low_periodicity      

ren log_deaths_pc ln_deaths_pc
ren y_activity    activity
ren log_light_emissions ln_ntl_median

gen ntl_median = light_emissions
recode ntl_median .=0.000000001
gen logntl = ln(ntl_median)

gen has_light = ((light_emissions > 0) & (light_emissions != .))

*gen ndvi_dev_control = ndvi_dev 
gen ndvi_dev_control = ndvi_ag_anom

*egen byte mkt_tag = tag(market_id) /*note  tag is 2018*/
gen byte mkt_tag_2020 = (year == `BASE')
cap drop ntl asin_ntl
gen ntl = exp(ln_ntl_median)
recode ntl . = 0
gen asin_ntl = asinh(ntl)


tab access, gen(A)
rename A1 Access_H
rename A2 Access_Int
rename A3 Access_R


gen double c_dist_osm         = ln(dist_osm) 
gen double c_dist_NoOverlap_osm = ln(dist_osm_NoOverlap) 

gen double c_travel_50         = asinh(travel_50) 
/* gen double c_dist_osm         =  dist_osm */
gen double c_ln_catchment_pop = ln_pop_30mixed

/* foreach v in low_periodicity c_dist_osm c_dist_NoOverlap_osm c_travel_50 c_ln_catchment_pop Access_H Access_Int Access_R {
    quietly summarize `v' if mkt_tag_2020 == 1, meanonly
    replace `v' = `v' - r(mean)
}
 */

foreach v in low_periodicity c_dist_osm c_dist_NoOverlap_osm c_travel_50 c_ln_catchment_pop Access_H Access_Int Access_R {
    forvalues y = 2018/2025 {
        if `y' != `BASE' {
            gen double X_`v'_`y' =  `v' if (year == `y')
            recode X_`v'_`y' .=0
            label var X_`v'_`y' "`v' x `y'"
        }
    }
}


* Output folders: regression tables to event_study, paper figures to paper_exhibits.
global out_file   = "$root/../output_paper/event_study"
global paper_out  = "$root/../output_paper/paper_exhibits"
cap mkdir "$out_file"
cap mkdir "$paper_out"


*==============================================================================
* POOLED REGRESSIONS
*
* All markets in one regression, market fixed effects, standard errors
* clustered by province. Controls in all three: NDVI anomaly and log deaths per
* capita. Table: MAI_pooled.xls (in event_study). Tests are printed in the log and
* added to the table as p-values. Figures: Figure 9 panels a-d (see the header).
*==============================================================================

*------------------------------------------------------------------------------
* PAPER FIGURE 9, panel a. Regression 1: activity on access x year.
* Each access group gets its own year path relative to 2020. The three sets
* together span the year effects, so there are no separate year dummies.
*------------------------------------------------------------------------------
reghdfe activity X_Access_H_20?? X_Access_Int_20?? X_Access_R_20?? ///
    ln_deaths_pc ndvi_dev_control, absorb(market_id) vce(cluster Prov_ID)
estimates store P1_access

* Do the three groups follow the same path? Year by year, then all years jointly.
di as txt _n "Reg 1: H = Int = R, by year"
local jt ""
forvalues y = 2018/2025 {
    if `y' != `BASE' {
        quietly test (X_Access_H_`y' = X_Access_Int_`y') (X_Access_H_`y' = X_Access_R_`y')
        di as txt "  `y':  F = " as res %6.2f r(F) as txt "   p = " as res %5.3f r(p)
        local jt `jt' (X_Access_H_`y' = X_Access_Int_`y') (X_Access_H_`y' = X_Access_R_`y')
    }
}
test `jt'
local p_same = r(p)

outreg2 using "$out_file/MAI_pooled.xls", replace bdec(3) sdec(2) ///
    alpha(0.001, 0.01, 0.05) symbol(***, **, *) addtext(Mkt FE, YES) ///
    addstat("p: same path all groups", `p_same') ctitle("1. Access x year")

* Year labels for the x axis (also defined above; repeated so this section runs alone)
local cn ""
local lb ""
forvalues k = 1/8 {
    local y = 2017 + `k'
    local cn `cn' y`y'
    local lb `lb' y`y' = "`y'"
}

* Figure: each access group's year path from the pooled regression. 90% intervals,
* as in the figures above; 2020 is the base year (0 by construction).
estimates restore P1_access
local tcrit = invttail(e(N_clust) - 1, 0.05)
local j = 0
foreach a in H Int R {
    local ++j
    matrix B_`j' = J(1, 8, 0)
    matrix C_`j' = J(2, 8, 0)
    forvalues k = 1/8 {
        local y = 2017 + `k'
        if `y' != `BASE' {
            matrix B_`j'[1, `k'] = _b[X_Access_`a'_`y']
            matrix C_`j'[1, `k'] = _b[X_Access_`a'_`y'] - `tcrit' * _se[X_Access_`a'_`y']
            matrix C_`j'[2, `k'] = _b[X_Access_`a'_`y'] + `tcrit' * _se[X_Access_`a'_`y']
        }
    }
    matrix colnames B_`j' = `cn'
    matrix colnames C_`j' = `cn'
}

coefplot (matrix(B_1), ci(C_1) label("High access") offset(-0.2)                          ///
             msymbol(O) mcolor("0 114 178") ciopts(recast(rcap) lcolor("0 114 178")))     ///
         (matrix(B_2), ci(C_2) label("Intermediate access") offset(0)                     ///
             msymbol(S) mcolor("230 159 0") ciopts(recast(rcap) lcolor("230 159 0")))     ///
         (matrix(B_3), ci(C_3) label("Remote") offset(0.2)                                ///
             msymbol(T) mcolor("0 158 115") ciopts(recast(rcap) lcolor("0 158 115"))),    ///
    vertical coeflabels(`lb')                                               ///
    yline(0, lcolor(black) lpattern(dash))                                  ///
    xline(3, lcolor(gs10))                                                  ///
    legend(rows(1) position(6) size(medium))                                ///
    xlabel(, angle(vertical) labsize(large))  ylabel(, labsize(large))      ///
    graphregion(margin(vsmall))                                             ///
    xsize(5) ysize(5.3)                                                     ///
    name(fig_pooled_access, replace)
graph export "$paper_out/fig09a_access_categories.png", replace width(2400)

*------------------------------------------------------------------------------
* PAPER FIGURE 9, panel b. Regression 2: density x year and travel time x year.
*   density     = ln_pop_30mixed, log of population within 30 minutes (mixed
*                 mode) of the market (catchment population)
*   travel time = travel_50, minutes to the nearest 50K town
* Both continuous, each interacted with every year except 2020:
*   D_dens_<y>   effect of 1 log point more catchment population in year y
*   D_trav_<y>   effect of 1 more minute of travel in year y
* Market and year fixed effects: the year effects absorb shocks common to all
* markets, so the interactions measure only differences across markets.
*------------------------------------------------------------------------------
summarize ln_pop_30mixed travel_50 if year == `BASE'

forvalues y = 2018/2025 {
    if `y' != `BASE' {
        gen double D_dens_`y' = ln_pop_30mixed * (year == `y')
        gen double D_trav_`y' = travel_50 * (year == `y')
        * asinh (inverse hyperbolic sine), not asin: asin is only defined on [-1, 1]
        * and returns missing for any travel time above 1 minute.
        gen double D_ASINtrav_`y' = asinh(travel_50) * (year == `y')
        label var D_dens_`y' "log catchment pop x `y'"
        label var D_trav_`y' "travel (min) x `y'"
        label var D_ASINtrav_`y' "asinh(travel) x `y'"
    }
}

reghdfe activity D_dens_20??  D_ASINtrav_20??  ///
    ln_deaths_pc ndvi_dev_control, absorb(market_id year) vce(cluster Prov_ID)
estimates store P2_dens_travel

* Joint tests over all years
di as txt _n "Reg 2: (a) density x year = 0"
testparm D_dens_20??
local p_dens = r(p)
di as txt _n "Reg 2: (b) asinh(travel) x year = 0"
testparm D_ASINtrav_20??
local p_ASINtrav = r(p)

outreg2 using "$out_file/MAI_pooled.xls", append bdec(3) sdec(2) ///
    alpha(0.001, 0.01, 0.05) symbol(***, **, *) addtext(Mkt FE, YES, Year FE, YES) ///
    addstat("p: density x year = 0", `p_dens', "p: asinh(travel) x year = 0", `p_ASINtrav') ///
    ctitle("2. Density, travel")

* Figure: density and travel coefficients in one figure, as estimated: density
* per log point on the left axis, asinh(travel) on the right axis. The two axes
* share the same zero line; the right-axis scale is set from the data, so if the
* two sets of coefficients are of similar size the axes simply match.
* 90% intervals.
local tcrit = invttail(e(N_clust) - 1, 0.05)
foreach t in dens ASINtrav {
    matrix B_`t' = J(1, 8, 0)
    matrix C_`t' = J(2, 8, 0)
    local lo_`t' = 0
    local hi_`t' = 0
    forvalues k = 1/8 {
        local y = 2017 + `k'
        if `y' != `BASE' {
            matrix B_`t'[1, `k'] = _b[D_`t'_`y']
            matrix C_`t'[1, `k'] = _b[D_`t'_`y'] - `tcrit' * _se[D_`t'_`y']
            matrix C_`t'[2, `k'] = _b[D_`t'_`y'] + `tcrit' * _se[D_`t'_`y']
            local lo_`t' = min(`lo_`t'', C_`t'[1, `k'])
            local hi_`t' = max(`hi_`t'', C_`t'[2, `k'])
        }
    }
    matrix colnames B_`t' = `cn'
    matrix colnames C_`t' = `cn'
}

* Right-axis scale r = travel units per density unit: the smallest round value
* that fits the travel intervals inside the density axis range.
local ratio = max(abs(`lo_ASINtrav'), abs(`hi_ASINtrav')) / max(abs(`lo_dens'), abs(`hi_dens'))
local r = 1
foreach c in 1 0.5 0.25 0.2 0.1 0.05 0.025 0.02 0.01 0.005 0.0025 0.002 0.001 {
    if `c' >= `ratio' local r = `c'
}
local L = min(`lo_dens', `lo_ASINtrav' / `r')
local U = max(`hi_dens', `hi_ASINtrav' / `r')
local step = cond(`U' - `L' > 30, 10, 5)
local L = floor(`L' / `step') * `step'
local U = ceil(`U' / `step') * `step'
local lab1 ""
local lab2 ""
forvalues v = `L'(`step')`U' {
    local lab1 `lab1' `v'
    local lab2 `lab2' `=`v' * `r''
}

coefplot (matrix(B_dens), ci(C_dens) label("Log catchment population (left axis)") offset(-0.15) ///
             msymbol(O) mcolor("0 114 178") ciopts(recast(rcap) lcolor("0 114 178")))          ///
         (matrix(B_ASINtrav), ci(C_ASINtrav) label("asinh(travel time) (right axis)") offset(0.15) ///
             msymbol(S) mcolor("230 159 0") ciopts(recast(rcap) lcolor("230 159 0")) axis(2)), ///
    vertical coeflabels(`lb')                                                     ///
    yline(0, lcolor(black) lpattern(dash))                                        ///
    xline(3, lcolor(gs10))                                                        ///
    ytitle("Index points per log point of population", axis(1))                  ///
    ytitle("Index points per unit of asinh(travel)", axis(2))                    ///
    yscale(range(`L' `U') axis(1)) ylabel(`lab1', labsize(large) axis(1))        ///
    yscale(range(`=`L'*`r'' `=`U'*`r'') axis(2))                                 ///
    ylabel(`lab2', labsize(large) format(%5.3g) angle(0) axis(2))                ///
    legend(rows(2) position(6) size(medium))                                      ///
    xlabel(, angle(vertical) labsize(large))                                      ///
    graphregion(margin(vsmall))                                                   ///
    xsize(5.5) ysize(5.5)                                                         ///
    name(fig_pooled_dens_travel, replace)
graph export "$paper_out/fig09b_population_travel.png", replace width(2400)

*------------------------------------------------------------------------------
* PAPER FIGURE 9, panel d. Regression 4: single-day x year and multi-day x year.
* Single-day = low_periodicity (once_a_week == 1); multi-day = the rest. Each
* group gets its own year path relative to 2020. The two sets together span the
* year effects, so there are no separate year dummies (as in regression 1).
*------------------------------------------------------------------------------
gen byte Single_day = (low_periodicity == 1)
gen byte Multi_day  = (low_periodicity == 0)
tab Single_day access if year == `BASE'

forvalues y = 2018/2025 {
    if `y' != `BASE' {
        gen double D_single_`y' = Single_day * (year == `y')
        gen double D_multi_`y'  = Multi_day  * (year == `y')
        label var D_single_`y' "single day x `y'"
        label var D_multi_`y'  "multi-day x `y'"
    }
}

reghdfe activity D_single_20?? D_multi_20?? ///
    ln_deaths_pc ndvi_dev_control, absorb(market_id) vce(cluster Prov_ID)
estimates store P4_single_multi

* Do the two groups follow the same path? Year by year, then all years jointly.
di as txt _n "Reg 4: single = multi, by year"
local jt ""
forvalues y = 2018/2025 {
    if `y' != `BASE' {
        quietly test D_single_`y' = D_multi_`y'
        di as txt "  `y':  F = " as res %6.2f r(F) as txt "   p = " as res %5.3f r(p)
        local jt `jt' (D_single_`y' = D_multi_`y')
    }
}
test `jt'
local p_same = r(p)

outreg2 using "$out_file/MAI_pooled.xls", append bdec(3) sdec(2) ///
    alpha(0.001, 0.01, 0.05) symbol(***, **, *) addtext(Mkt FE, YES) ///
    addstat("p: same path both groups", `p_same') ctitle("4. Single vs multi-day")

* Figure: both groups' year paths. 90% intervals.
local tcrit = invttail(e(N_clust) - 1, 0.05)
foreach t in single multi {
    matrix B_`t' = J(1, 8, 0)
    matrix C_`t' = J(2, 8, 0)
    forvalues k = 1/8 {
        local y = 2017 + `k'
        if `y' != `BASE' {
            matrix B_`t'[1, `k'] = _b[D_`t'_`y']
            matrix C_`t'[1, `k'] = _b[D_`t'_`y'] - `tcrit' * _se[D_`t'_`y']
            matrix C_`t'[2, `k'] = _b[D_`t'_`y'] + `tcrit' * _se[D_`t'_`y']
        }
    }
    matrix colnames B_`t' = `cn'
    matrix colnames C_`t' = `cn'
}

coefplot (matrix(B_single), ci(C_single) label("Single-day markets") offset(-0.15)  ///
             msymbol(O) mcolor("0 114 178") ciopts(recast(rcap) lcolor("0 114 178")))  ///
         (matrix(B_multi), ci(C_multi) label("Multi-day markets") offset(0.15)      ///
             msymbol(S) mcolor("230 159 0") ciopts(recast(rcap) lcolor("230 159 0"))), ///
    vertical coeflabels(`lb')                                               ///
    yline(0, lcolor(black) lpattern(dash))                                  ///
    xline(3, lcolor(gs10))                                                  ///
    ytitle("Index points")                                                  ///
    legend(rows(1) position(6) size(medium))                                ///
    xlabel(, angle(vertical) labsize(large))  ylabel(, labsize(large))      ///
    graphregion(margin(vsmall))                                             ///
    xsize(5) ysize(5.3)                                                     ///
    name(fig_pooled_single_multi, replace)
graph export "$paper_out/fig09d_single_multi_day.png", replace width(2400)

*------------------------------------------------------------------------------
* PAPER FIGURE 9, panel c. Regression 3: markets that trade on two days a week. Is activity the same on
* both days, year by year?
*
* Data: event_study_days_panel.dta (data_build/build_event_study_days_panel.py),
* one row per market x trading day x year, 32 markets. The outcome is each day's
* activity on the same scale as y_activity (the market's pooled 2020 level = 100).
* day_b marks the later of the two days in the Saturday-Friday week.
*
* Baseline specification:
*   reghdfe y_activity_day D_dayB_20?? ln_deaths_pc ndvi_dev_control
*           Access_H Access_Int Access_R, absorb(market_id) vce(cluster Prov_ID)
* extended with D_dayA_<y> = first day x year, so both days get a year path.
* D_dayA_2020 is left out: the 16 day x year dummies add up to 1, which the market
* FE already absorb. Both paths are therefore relative to the FIRST day in 2020:
*   D_dayA_<y>   first trading day in year y   (2020 = 0 by construction)
*   D_dayB_<y>   second trading day in year y  (2020 = gap to the first day)
* The gap between the days in year y is D_dayB_<y> - D_dayA_<y>.
* Access_H/Int/R do not change within a market, so the market FE absorb them and
* Stata reports them as omitted; they are kept to match the baseline.
*------------------------------------------------------------------------------
preserve
use "$root/event_study_days_panel.dta", clear

egen market_id = group(mktID)
rename log_deaths_pc ln_deaths_pc
gen ndvi_dev_control = ndvi_ag_anom

gen byte Access_H   = (access == "High access")
gen byte Access_Int = (access == "Intermediate access")
gen byte Access_R   = (access == "Remote")
tab access day_b if year == `BASE'

forvalues y = 2018/2025 {
    gen double D_dayB_`y' = day_b * (year == `y')
    label var D_dayB_`y' "second day x `y'"
    if `y' != `BASE' {
        gen double D_dayA_`y' = (1 - day_b) * (year == `y')
        label var D_dayA_`y' "first day x `y'"
    }
}

reghdfe y_activity_day D_dayA_20?? D_dayB_20?? ln_deaths_pc ndvi_dev_control ///
    Access_H Access_Int Access_R, absorb(market_id) vce(cluster Prov_ID)
estimates store P3_two_days
di as txt "Clusters (provinces): " as res e(N_clust)

* Gap (second minus first day) by year
di as txt _n "Reg 3: second day - first day, by year"
forvalues y = 2018/2025 {
    if `y' == `BASE' quietly lincom D_dayB_`y'
    else             quietly lincom D_dayB_`y' - D_dayA_`y'
    di as txt "  `y':  gap = " as res %6.2f r(estimate) as txt "   se = " ///
        as res %5.2f r(se) as txt "   p = " as res %5.3f r(p)
}

* (a) no gap in any year
di as txt _n "Reg 3: (a) same activity on both days in every year"
local eq "(D_dayB_`BASE' = 0)"
forvalues y = 2018/2025 {
    if `y' != `BASE' local eq `eq' (D_dayB_`y' = D_dayA_`y')
}
test `eq'
local p_nogap = r(p)

* (b) the gap is the same every year (it may be non-zero, but does not change)
di as txt _n "Reg 3: (b) gap equal across years"
local eq ""
forvalues y = 2019/2025 {
    if `y' == `BASE' local eq `eq' (D_dayB_2018 - D_dayA_2018 = D_dayB_`y')
    else             local eq `eq' (D_dayB_2018 - D_dayA_2018 = D_dayB_`y' - D_dayA_`y')
}
test `eq'
local p_stable = r(p)

outreg2 using "$out_file/MAI_pooled.xls", append bdec(3) sdec(2) ///
    alpha(0.001, 0.01, 0.05) symbol(***, **, *) addtext(Mkt FE, YES) ///
    addstat("p: no gap any year", `p_nogap', "p: gap same each year", `p_stable') ///
    ctitle("3. Two-day markets")

* Figure: both days' year paths, relative to the first day in 2020. 90% intervals.
local tcrit = invttail(e(N_clust) - 1, 0.05)
matrix B_A = J(1, 8, 0)
matrix C_A = J(2, 8, 0)
matrix B_B = J(1, 8, 0)
matrix C_B = J(2, 8, 0)
forvalues k = 1/8 {
    local y = 2017 + `k'
    matrix B_B[1, `k'] = _b[D_dayB_`y']
    matrix C_B[1, `k'] = _b[D_dayB_`y'] - `tcrit' * _se[D_dayB_`y']
    matrix C_B[2, `k'] = _b[D_dayB_`y'] + `tcrit' * _se[D_dayB_`y']
    if `y' != `BASE' {
        matrix B_A[1, `k'] = _b[D_dayA_`y']
        matrix C_A[1, `k'] = _b[D_dayA_`y'] - `tcrit' * _se[D_dayA_`y']
        matrix C_A[2, `k'] = _b[D_dayA_`y'] + `tcrit' * _se[D_dayA_`y']
    }
}
foreach M in B_A C_A B_B C_B {
    matrix colnames `M' = `cn'
}

coefplot (matrix(B_A), ci(C_A) label("First trading day") offset(-0.15)                ///
             msymbol(O) mcolor("0 114 178") ciopts(recast(rcap) lcolor("0 114 178")))  ///
         (matrix(B_B), ci(C_B) label("Second trading day") offset(0.15)                ///
             msymbol(S) mcolor("230 159 0") ciopts(recast(rcap) lcolor("230 159 0"))), ///
    vertical coeflabels(`lb')                                               ///
    yline(0, lcolor(black) lpattern(dash))                                  ///
    xline(3, lcolor(gs10))                                                  ///
    note("Relative to the first trading day in 2020." "Days ordered Saturday-Friday.", size(small)) ///
    legend(rows(1) position(6) size(medium))                                ///
    xlabel(, angle(vertical) labsize(large))  ylabel(, labsize(large))      ///
    graphregion(margin(vsmall))                                             ///
    xsize(5) ysize(5.3)                                                     ///
    name(fig_two_day_markets, replace)
graph export "$paper_out/fig09c_two_day_markets.png", replace width(2400)
restore


*==============================================================================
* PAPER FIGURE 10, panel a. NIGHTTIME LIGHTS BY ACCESS, WITHOUT THE TRADING-FREQUENCY TERMS
*
* Same specification as the NTL regressions at the top of the file (asinh of
* NTL, one regression per access group, market FE, province clusters, deaths and
* NDVI controls), but without the single/multi-day terms (X_low_periodicity_*
* and X_Access_*_per*). Each regression keeps only its own group's year
* dummies, so the coefficients are that group's year path relative to 2020.
* Table: NTL_access.xls. Figure: fig_NTL_access_noperiodicity.png.
*==============================================================================
foreach a in H Int R {
    reghdfe asin_ntl X_Access_`a'_20?? ln_deaths_pc ndvi_dev_control ///
        if Access_`a' == 1, absorb(market_id) vce(cluster Prov_ID)
    estimates store N_Access_`a'

    if "`a'" == "H" local rep replace
    else            local rep append
    outreg2 using "$out_file/NTL_access.xls", `rep' bdec(3) sdec(2) ///
        alpha(0.001, 0.01, 0.05) symbol(***, **, *) addtext(Mkt FE, YES) ///
        ctitle("NTL Access_`a'")
}

* Figure: the three year paths, one per regression. 90% intervals, as above.
local j = 0
foreach a in H Int R {
    local ++j
    estimates restore N_Access_`a'
    local tcrit = invttail(e(N_clust) - 1, 0.05)
    matrix B_`j' = J(1, 8, 0)
    matrix C_`j' = J(2, 8, 0)
    forvalues k = 1/8 {
        local y = 2017 + `k'
        if `y' != `BASE' {
            matrix B_`j'[1, `k'] = _b[X_Access_`a'_`y']
            matrix C_`j'[1, `k'] = _b[X_Access_`a'_`y'] - `tcrit' * _se[X_Access_`a'_`y']
            matrix C_`j'[2, `k'] = _b[X_Access_`a'_`y'] + `tcrit' * _se[X_Access_`a'_`y']
        }
    }
    matrix colnames B_`j' = `cn'
    matrix colnames C_`j' = `cn'
}

coefplot (matrix(B_1), ci(C_1) label("High access") offset(-0.2)                          ///
             msymbol(O) mcolor("0 114 178") ciopts(recast(rcap) lcolor("0 114 178")))     ///
         (matrix(B_2), ci(C_2) label("Intermediate access") offset(0)                     ///
             msymbol(S) mcolor("230 159 0") ciopts(recast(rcap) lcolor("230 159 0")))     ///
         (matrix(B_3), ci(C_3) label("Remote") offset(0.2)                                ///
             msymbol(T) mcolor("0 158 115") ciopts(recast(rcap) lcolor("0 158 115"))),    ///
    vertical coeflabels(`lb')                                               ///
    yline(0, lcolor(black) lpattern(dash))                                  ///
    xline(3, lcolor(gs10))                                                  ///
    ytitle("asinh(NTL), change from 2020")                                  ///
    legend(rows(1) position(6) size(medium))                                ///
    xlabel(, angle(vertical) labsize(large))  ylabel(, labsize(large))      ///
    graphregion(margin(vsmall))                                             ///
    xsize(5) ysize(5.3)                                                     ///
    name(fig_NTL_access_noper, replace)
graph export "$paper_out/fig10a_ntl_access_categories.png", replace width(2400)


*------------------------------------------------------------------------------
* PAPER FIGURE 10, panel b. NTL version of regression 2: density x year and travel time x year, with
* asinh(NTL) as the outcome. Same terms as regression 2 (D_dens_<y> = log
* catchment population x year, D_ASINtrav_<y> = asinh(travel minutes) x year),
* market and year FE, deaths and NDVI controls, province clusters.
* Added as the last column of NTL_access.xls.
*------------------------------------------------------------------------------
reghdfe asin_ntl D_dens_20?? D_ASINtrav_20?? ///
    ln_deaths_pc ndvi_dev_control, absorb(market_id year) vce(cluster Prov_ID)
estimates store N2_dens_travel

di as txt _n "NTL reg 2: (a) density x year = 0"
testparm D_dens_20??
local p_dens = r(p)
di as txt _n "NTL reg 2: (b) asinh(travel) x year = 0"
testparm D_ASINtrav_20??
local p_ASINtrav = r(p)

outreg2 using "$out_file/NTL_access.xls", append bdec(3) sdec(2) ///
    alpha(0.001, 0.01, 0.05) symbol(***, **, *) addtext(Mkt FE, YES, Year FE, YES) ///
    addstat("p: density x year = 0", `p_dens', "p: asinh(travel) x year = 0", `p_ASINtrav') ///
    ctitle("NTL density, travel")

* Figure: both sets of coefficients on one axis (log points of population and
* asinh units of travel are on similar scales). 90% intervals.
local tcrit = invttail(e(N_clust) - 1, 0.05)
foreach t in dens ASINtrav {
    matrix B_`t' = J(1, 8, 0)
    matrix C_`t' = J(2, 8, 0)
    forvalues k = 1/8 {
        local y = 2017 + `k'
        if `y' != `BASE' {
            matrix B_`t'[1, `k'] = _b[D_`t'_`y']
            matrix C_`t'[1, `k'] = _b[D_`t'_`y'] - `tcrit' * _se[D_`t'_`y']
            matrix C_`t'[2, `k'] = _b[D_`t'_`y'] + `tcrit' * _se[D_`t'_`y']
        }
    }
    matrix colnames B_`t' = `cn'
    matrix colnames C_`t' = `cn'
}

coefplot (matrix(B_dens), ci(C_dens) label("Log catchment population") offset(-0.15)   ///
             msymbol(O) mcolor("0 114 178") ciopts(recast(rcap) lcolor("0 114 178")))   ///
         (matrix(B_ASINtrav), ci(C_ASINtrav) label("asinh(travel time)") offset(0.15)  ///
             msymbol(S) mcolor("230 159 0") ciopts(recast(rcap) lcolor("230 159 0"))),  ///
    vertical coeflabels(`lb')                                               ///
    yline(0, lcolor(black) lpattern(dash))                                  ///
    xline(3, lcolor(gs10))                                                  ///
    ytitle("asinh(NTL) per unit")                                           ///
    legend(rows(1) position(6) size(medsmall))                              ///
    xlabel(, angle(vertical) labsize(large))  ylabel(, labsize(large))      ///
    graphregion(margin(vsmall))                                             ///
    xsize(5) ysize(5.3)                                                     ///
    name(fig_NTL_dens_travel, replace)
graph export "$paper_out/fig10b_ntl_population_travel.png", replace width(2400)

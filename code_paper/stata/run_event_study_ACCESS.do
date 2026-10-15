*------------------------------------------------------------------------------
* MAI event study — Models A and B
*
* Mirrors section 5 of Results_paper.ipynb.
*
* Input : event_study_panel.dta, built by build_event_study_panel.ipynb
* Output: three stored estimates, one table, joint tests, two plots per model
*
* ssc install reghdfe,  replace
* ssc install ftools,   replace
* ssc install coefplot, replace
* ssc install estout,   replace
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


foreach v in  Access_H Access_Int Access_R {
    forvalues y = 2018/2025 {
        if `y' != `BASE' {

            gen double X_`v'_per`y' =  `v'*X_low_periodicity_`y'
            recode X_`v'_per`y' .=0
            label var X_`v'_per`y' "`v' x `y'"
        }
    }
}


/* local RHS X_low_periodicity_*  X_Access_H_per* X_Access_Int_per* X_Access_R_per* ln_deaths_pc ndvi_dev_control */
local RHS X_low_periodicity_*  X_Access_H* X_Access_Int* X_Access_R* ln_deaths_pc ndvi_dev_control 


* Outputs go to output_paper/event_study, next to processed_data (set by $root above).
global out_file = "$root/../output_paper/event_study"
cap mkdir "$out_file"


reghdfe activity  `RHS' if Access_H == 1 , absorb(market_id) vce(cluster Prov_ID)

outreg2 using "$out_file/MAI_access.xls", replace bdec(3) sdec(2) alpha(0.001, 0.01, 0.05) symbol(***, **, *)  addtext(Mkt FE, YES)  ctitle("MAI Access_H") 
estimates store A_Access_H

reghdfe activity  `RHS' if Access_Int == 1 , absorb(market_id) vce(cluster Prov_ID)
outreg2 using "$out_file/MAI_access.xls", append bdec(3) sdec(2) alpha(0.001, 0.01, 0.05) symbol(***, **, *)  addtext(Mkt FE, YES)  ctitle("MAI Access_Int") 
estimates store A_Access_Int

reghdfe activity  `RHS' if Access_R == 1 , absorb(market_id) vce(cluster Prov_ID)
outreg2 using "$out_file/MAI_access.xls", append bdec(3) sdec(2) alpha(0.001, 0.01, 0.05) symbol(***, **, *)  addtext(Mkt FE, YES)  ctitle("MAI Access_R") 
estimates store A_Access_R


reghdfe asin_ntl  `RHS' if Access_H == 1 , absorb(market_id) vce(cluster Prov_ID)
outreg2 using "$out_file/MAI_access.xls", append bdec(3) sdec(2) alpha(0.001, 0.01, 0.05) symbol(***, **, *)  addtext(Mkt FE, YES)  ctitle("MAI Access_H") 
estimates store A_Access_H_NLT

reghdfe asin_ntl  `RHS' if Access_Int == 1 , absorb(market_id) vce(cluster Prov_ID)
outreg2 using "$out_file/MAI_access.xls", append bdec(3) sdec(2) alpha(0.001, 0.01, 0.05) symbol(***, **, *)  addtext(Mkt FE, YES)  ctitle("MAI Access_Int") 
estimates store A_Access_Int_NLT

reghdfe asin_ntl  `RHS' if Access_R == 1 , absorb(market_id) vce(cluster Prov_ID)
outreg2 using "$out_file/MAI_access.xls", append bdec(3) sdec(2) alpha(0.001, 0.01, 0.05) symbol(***, **, *)  addtext(Mkt FE, YES)  ctitle("MAI Access_R") 
estimates store A_Access_R_NLT

*------------------------------------------------------------------------------
* Figures. For each outcome (MAI, NTL), two figures that overlay the three
* access regressions (high, intermediate, remote):
*   1. X_low_periodicity_<year>       once-a-week trading x year
*   2. X_Access_<level>_<year>        each access level's own year path, from its
*                                     own regression (high from the high-access
*                                     sample, and so on)
* Points are offset so the intervals do not overlap. Colours are Okabe-Ito blue,
* orange and green, and the markers differ too, so identity is not colour alone.
*------------------------------------------------------------------------------

* Year labels for the x axis (2018-2025; 2020 is the omitted base year)
local cn ""
local lb ""
forvalues k = 1/8 {
    local y = 2017 + `k'
    local cn `cn' y`y'
    local lb `lb' y`y' = "`y'"
}

foreach out in MAI NTL {

    if "`out'" == "MAI" {
        local sfx  ""
        local otitle "Market activity"
    }
    if "`out'" == "NTL" {
        local sfx  "_NLT"
        local otitle "Nighttime lights"
    }

    * P_j: low-periodicity coefficients; T_j: access-level year path; j = 1 high, 2 intermediate, 3 remote
    local j = 0
    foreach a in H Int R {
        local ++j
        estimates restore A_Access_`a'`sfx'
        /* local tcrit = invttail(e(N_clust) - 1, 0.025) */
        local tcrit = invttail(e(N_clust) - 1, 0.05)

        matrix P_`j'  = J(1, 8, 0)
        matrix PCI_`j' = J(2, 8, 0)
        matrix T_`j'  = J(1, 8, 0)
        matrix TCI_`j' = J(2, 8, 0)
        forvalues k = 1/8 {
            local y = 2017 + `k'
            if `y' != `BASE' {
                matrix P_`j'[1, `k']   = _b[X_low_periodicity_`y']
                matrix PCI_`j'[1, `k'] = _b[X_low_periodicity_`y'] - `tcrit' * _se[X_low_periodicity_`y']
                matrix PCI_`j'[2, `k'] = _b[X_low_periodicity_`y'] + `tcrit' * _se[X_low_periodicity_`y']

                matrix T_`j'[1, `k']   = _b[X_Access_`a'_`y']
                matrix TCI_`j'[1, `k'] = _b[X_Access_`a'_`y'] - `tcrit' * _se[X_Access_`a'_`y']
                matrix TCI_`j'[2, `k'] = _b[X_Access_`a'_`y'] + `tcrit' * _se[X_Access_`a'_`y']
            }
        }
        foreach M in P_`j' PCI_`j' T_`j' TCI_`j' {
            matrix colnames `M' = `cn'
        }
    }

    * Figure 1: once-a-week trading x year, by access level
    coefplot (matrix(P_1), ci(PCI_1) label("High access") offset(-0.2)                                    ///
                 msymbol(O) mcolor("0 114 178") ciopts(recast(rcap) lcolor("0 114 178")))               ///
             (matrix(P_2), ci(PCI_2) label("Intermediate access") offset(0)                             ///
                 msymbol(S) mcolor("230 159 0") ciopts(recast(rcap) lcolor("230 159 0")))               ///
             (matrix(P_3), ci(PCI_3) label("Remote") offset(0.2)                                        ///
                 msymbol(T) mcolor("0 158 115") ciopts(recast(rcap) lcolor("0 158 115"))),              ///
        vertical coeflabels(`lb')                                               ///
        yline(0, lcolor(black) lpattern(dash))                                  ///
        xline(3, lcolor(gs10))                                                  ///
        title("`otitle': once-a-week trading, by market access", size(medium))  ///
        legend(rows(1) position(6) size(medium))                                ///
		xlabel(, angle(vertical) labsize(large))  ylabel(, labsize(large))   	///
		graphregion(margin(vsmall))                                             ///
		xsize(5) ysize(5) aspectratio(1)                                        ///
        name(fig_`out'_periodicity, replace)
    graph export "$out_file/fig_`out'_low_periodicity.png", replace width(2400)

    * Figure 2: each access level's year path
    coefplot (matrix(T_1), ci(TCI_1) label("High access") offset(-0.2)                                    ///
                 msymbol(O) mcolor("0 114 178") ciopts(recast(rcap) lcolor("0 114 178")))               ///
             (matrix(T_2), ci(TCI_2) label("Intermediate access") offset(0)                             ///
                 msymbol(S) mcolor("230 159 0") ciopts(recast(rcap) lcolor("230 159 0")))               ///
             (matrix(T_3), ci(TCI_3) label("Remote") offset(0.2)                                        ///
                 msymbol(T) mcolor("0 158 115") ciopts(recast(rcap) lcolor("0 158 115"))),              ///
        vertical coeflabels(`lb')                                               ///
        yline(0, lcolor(black) lpattern(dash))                                  ///
        xline(3, lcolor(gs10))                                                  ///
        title("`otitle': market access", size(medium))                          ///
        legend(rows(1) position(6) size(medium))                                ///
		xlabel(, angle(vertical) labsize(large))  ylabel(, labsize(large))   	///
		graphregion(margin(vsmall))                                             ///
		xsize(5) ysize(5) aspectratio(1)                                        ///
        name(fig_`out'_access, replace)
    graph export "$out_file/fig_`out'_access.png", replace width(2400)
}

*------------------------------------------------------------------------------
* Figures, one per regression. Each of the six regressions (MAI and NTL, for
* high-access, intermediate-access and remote markets) gets a single figure that
* plots both of its coefficient sets on the same axes:
*   X_Access_<level>_<year>   the access group's year path relative to 2020,
*                             i.e. markets trading more than once a week
*   X_low_periodicity_<year>  the additional change for once-weekly markets
* The path of once-weekly markets is the sum of the two. Same 90% intervals as the
* overlay figures above; the two series keep the same colours in all six figures.
* These are the paper's Figure 10 panels b-d (MAI) and Figure 11 (NTL).
*------------------------------------------------------------------------------
foreach out in MAI NTL {

    if "`out'" == "MAI" {
        local sfx  ""
        local otitle "Market activity"
    }
    if "`out'" == "NTL" {
        local sfx  "_NLT"
        local otitle "Nighttime lights"
    }

    foreach a in H Int R {
        if "`a'" == "H"   local atitle "High-access markets"
        if "`a'" == "Int" local atitle "Intermediate-access markets"
        if "`a'" == "R"   local atitle "Remote markets"

        local m A_Access_`a'`sfx'
        estimates restore `m'
        local tcrit = invttail(e(N_clust) - 1, 0.05)

        matrix Tm  = J(1, 8, 0)
        matrix TCm = J(2, 8, 0)
        matrix Pm  = J(1, 8, 0)
        matrix PCm = J(2, 8, 0)
        forvalues k = 1/8 {
            local y = 2017 + `k'
            if `y' != `BASE' {
                matrix Tm[1, `k']  = _b[X_Access_`a'_`y']
                matrix TCm[1, `k'] = _b[X_Access_`a'_`y'] - `tcrit' * _se[X_Access_`a'_`y']
                matrix TCm[2, `k'] = _b[X_Access_`a'_`y'] + `tcrit' * _se[X_Access_`a'_`y']

                matrix Pm[1, `k']  = _b[X_low_periodicity_`y']
                matrix PCm[1, `k'] = _b[X_low_periodicity_`y'] - `tcrit' * _se[X_low_periodicity_`y']
                matrix PCm[2, `k'] = _b[X_low_periodicity_`y'] + `tcrit' * _se[X_low_periodicity_`y']
            }
        }
        foreach M in Tm TCm Pm PCm {
            matrix colnames `M' = `cn'
        }

        * One figure per regression: both sets of coefficients on the same axes, offset so
        * the intervals do not overlap. The two series keep the same colours in every figure:
        * blue circles for multiple-day markets (the year path), orange squares for the
        * once-a-week coefficients.
        coefplot (matrix(Tm), ci(TCm) label("Multiple day markets") offset(-0.15)                ///
                     msymbol(O) mcolor("0 114 178") ciopts(recast(rcap) lcolor("0 114 178")))   ///
                 (matrix(Pm), ci(PCm) label("Daily markets") offset(0.15)                       ///
                     msymbol(S) mcolor("230 159 0") ciopts(recast(rcap) lcolor("230 159 0"))),  ///
            vertical coeflabels(`lb')                                           ///
            yline(0, lcolor(black) lpattern(dash))                              ///
            xline(3, lcolor(gs10))                                              ///
            title("`otitle': `atitle'", size(medium))                           ///
            legend(rows(1) position(6) size(medium))                            ///
            xlabel(, angle(vertical) labsize(large))  ylabel(, labsize(large))  ///
            graphregion(margin(vsmall))                                         ///
            xsize(5) ysize(5.3)                                                 ///
            name(fig_`m', replace)
        graph export "$out_file/fig_`m'.png", replace width(2400)
    }
}

*------------------------------------------------------------------------------
* Levels version of the six figures above. Same regressions, but the orange series
* is the year path of once-weekly markets themselves, theta_y + beta_y, instead of
* their additional change beta_y:
*   blue    X_Access_<level>_<year>                            multi-day markets
*   orange  X_Access_<level>_<year> + X_low_periodicity_<year>  once-weekly markets
* Both are relative to 2020. The once-weekly standard error comes from lincom, so it
* includes the covariance of theta_y and beta_y. Same 90% intervals as above.
* Every year's theta_y, beta_y and theta_y + beta_y, with p-values, is also written
* to MAI_access_levels.csv.
*------------------------------------------------------------------------------
tempname fh
file open `fh' using "$out_file/MAI_access_levels.csv", write replace
file write `fh' "outcome,access,year,series,coef,se,p,ci90_lo,ci90_hi,N,clusters" _n

foreach out in MAI NTL {

    if "`out'" == "MAI" {
        local sfx  ""
        local otitle "Market activity"
    }
    if "`out'" == "NTL" {
        local sfx  "_NLT"
        local otitle "Nighttime lights"
    }

    foreach a in H Int R {
        if "`a'" == "H"   local atitle "High-access markets"
        if "`a'" == "Int" local atitle "Intermediate-access markets"
        if "`a'" == "R"   local atitle "Remote markets"

        local m A_Access_`a'`sfx'
        estimates restore `m'
        local tcrit = invttail(e(N_clust) - 1, 0.05)
        local N = e(N)
        local G = e(N_clust)

        matrix Tm  = J(1, 8, 0)
        matrix TCm = J(2, 8, 0)
        matrix Lm  = J(1, 8, 0)
        matrix LCm = J(2, 8, 0)
        forvalues k = 1/8 {
            local y = 2017 + `k'
            if `y' != `BASE' {
                foreach s in multi_day once_weekly_diff once_weekly_level {
                    if "`s'" == "multi_day"         quietly lincom X_Access_`a'_`y'
                    if "`s'" == "once_weekly_diff"  quietly lincom X_low_periodicity_`y'
                    if "`s'" == "once_weekly_level" quietly lincom X_Access_`a'_`y' + X_low_periodicity_`y'
                    local b  = r(estimate)
                    local se = r(se)
                    local lo = `b' - `tcrit' * `se'
                    local hi = `b' + `tcrit' * `se'
                    local row "`out',`a',`y',`s'"
                    foreach v in b se p lo hi {
                        if "`v'" == "p" local x = r(p)
                        else            local x = ``v''
                        local row "`row',`=strtrim(string(`x', "%12.6g"))'"
                    }
                    file write `fh' "`row',`N',`G'" _n

                    if "`s'" == "multi_day" {
                        matrix Tm[1, `k']  = `b'
                        matrix TCm[1, `k'] = `lo'
                        matrix TCm[2, `k'] = `hi'
                    }
                    if "`s'" == "once_weekly_level" {
                        matrix Lm[1, `k']  = `b'
                        matrix LCm[1, `k'] = `lo'
                        matrix LCm[2, `k'] = `hi'
                    }
                }
            }
        }
        foreach M in Tm TCm Lm LCm {
            matrix colnames `M' = `cn'
        }

        coefplot (matrix(Tm), ci(TCm) label("Multiple day markets") offset(-0.15)               ///
                     msymbol(O) mcolor("0 114 178") ciopts(recast(rcap) lcolor("0 114 178")))  ///
                 (matrix(Lm), ci(LCm) label("Once-weekly markets") offset(0.15)                ///
                     msymbol(S) mcolor("230 159 0") ciopts(recast(rcap) lcolor("230 159 0"))), ///
            vertical coeflabels(`lb')                                           ///
            yline(0, lcolor(black) lpattern(dash))                              ///
            xline(3, lcolor(gs10))                                              ///
            title("`otitle': `atitle'", size(medium))                           ///
            legend(rows(1) position(6) size(medium))                            ///
            xlabel(, angle(vertical) labsize(large))  ylabel(, labsize(large))  ///
            graphregion(margin(vsmall))                                         ///
            xsize(5) ysize(5.3)                                                 ///
            name(fig_`m'_levels, replace)
        graph export "$out_file/fig_`m'_levels.png", replace width(2400)
    }
}
file close `fh'

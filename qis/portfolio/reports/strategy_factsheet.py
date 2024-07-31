"""
generate portfolio factsheet report using PortfolioData object
PortfolioData object can be generated by a backtester or actucal strategy data
with comparison to 1-2 cash benchmarks
PortfolioData can contain either simulated or actual portfolio data
"""
# packages
import pandas as pd
import matplotlib.pyplot as plt
from typing import Tuple, Optional, List
import qis as qis
from qis import TimePeriod, PerfParams, BenchmarkReturnsQuantileRegimeSpecs
from qis.portfolio.portfolio_data import PortfolioData
from qis.portfolio.reports.config import PERF_PARAMS, REGIME_PARAMS


def generate_strategy_factsheet(portfolio_data: PortfolioData,
                                benchmark_prices: pd.DataFrame,
                                time_period: TimePeriod,
                                perf_params: PerfParams = PERF_PARAMS,
                                regime_params: BenchmarkReturnsQuantileRegimeSpecs = REGIME_PARAMS,
                                regime_benchmark: str = None,  # default is set to benchmark_prices.columns[0]
                                exposures_freq: Optional[str] = 'W-WED',  #'W-WED',
                                turnover_rolling_period: int = 260,
                                turnover_title: Optional[str] = None,
                                factor_beta_span: int = 52,
                                beta_freq: str = 'W-WED',
                                factor_beta_title: Optional[str] = None,
                                factor_attribution_title: Optional[str] = None,
                                add_all_benchmarks_to_nav_figure: bool = False,
                                figsize: Tuple[float, float] = (8.3, 11.7),  # A4 for portrait
                                fontsize: int = 4,
                                add_var_risk_sheet: bool = True,
                                add_grouped_exposures: bool = False,
                                add_grouped_cum_pnl: bool = False,
                                is_1y_exposures: bool = False,
                                **kwargs
                                ) -> List[plt.Figure]:
    # align
    benchmark_prices = benchmark_prices.reindex(index=portfolio_data.nav.index, method='ffill')
    if regime_benchmark is None:
        regime_benchmark = benchmark_prices.columns[0]

    if portfolio_data.group_data is not None and len(portfolio_data.group_data.unique()) <= 7:  # otherwise tables look too bad
        is_grouped = True
    else:
        is_grouped = False

    fig = plt.figure(figsize=figsize, constrained_layout=True)
    gs = fig.add_gridspec(nrows=14, ncols=4, wspace=0.0, hspace=0.0)

    plot_kwargs = dict(fontsize=fontsize,
                       linewidth=0.5,
                       digits_to_show=1, sharpe_digits=2,
                       weight='normal',
                       markersize=1,
                       framealpha=0.75)
    kwargs = qis.update_kwargs(kwargs, plot_kwargs)
    fig.suptitle(f"{portfolio_data.nav.name} factsheet", fontweight="bold", fontsize=8, color='blue')

    # prices
    portfolio_nav = portfolio_data.get_portfolio_nav(time_period=time_period)
    if add_all_benchmarks_to_nav_figure:
        benchmark_prices_ = benchmark_prices
    else:
        benchmark_prices_ = benchmark_prices[regime_benchmark]
    joint_prices = pd.concat([portfolio_nav, benchmark_prices_], axis=1).dropna()
    pivot_prices = joint_prices[regime_benchmark]
    ax = fig.add_subplot(gs[0:2, :2])
    qis.plot_prices(prices=joint_prices,
                    perf_params=perf_params,
                    title='Performance',
                    ax=ax,
                    **kwargs)
    qis.add_bnb_regime_shadows(ax=ax, pivot_prices=pivot_prices, regime_params=regime_params)
    qis.set_spines(ax=ax, bottom_spine=False, left_spine=False)

    # dd
    ax = fig.add_subplot(gs[2:4, :2])
    qis.plot_rolling_drawdowns(prices=joint_prices,
                               title='Running Drawdowns',
                               dd_legend_type=qis.DdLegendType.DETAILED,
                               ax=ax, **kwargs)
    qis.add_bnb_regime_shadows(ax=ax, pivot_prices=pivot_prices, regime_params=regime_params)
    qis.set_spines(ax=ax, bottom_spine=False, left_spine=False)

    # under watre
    ax = fig.add_subplot(gs[4:6, :2])
    qis.plot_rolling_time_under_water(prices=joint_prices,
                                      title='Running Time under Water',
                                      dd_legend_type=qis.DdLegendType.DETAILED,
                                      ax=ax, **kwargs)
    qis.add_bnb_regime_shadows(ax=ax, pivot_prices=pivot_prices, regime_params=regime_params)
    qis.set_spines(ax=ax, bottom_spine=False, left_spine=False)

    # exposures
    if len(portfolio_data.weights.columns) > 10:  # more than 10 use grouped exposures
        exposures = portfolio_data.get_weights(is_grouped=True, time_period=time_period,
                                               add_total=False)
    else:
        exposures = portfolio_data.get_weights(is_grouped=False, time_period=time_period,
                                               add_total=False)
    ax = fig.add_subplot(gs[6:8, :2])
    if exposures_freq is not None:
        exposures = exposures.resample(exposures_freq).last()
    qis.plot_stack(df=exposures,
                   use_bar_plot=True,
                   title='Exposures',
                   legend_stats=qis.LegendStats.AVG_NONNAN_LAST,
                   var_format='{:.1%}',
                   ax=ax,
                   **qis.update_kwargs(kwargs, dict(bbox_to_anchor=(0.5, 1.05), ncol=2)))
    qis.set_spines(ax=ax, bottom_spine=False, left_spine=False)

    # turnover
    ax = fig.add_subplot(gs[8:10, :2])
    turnover = portfolio_data.get_turnover(time_period=time_period, roll_period=turnover_rolling_period)
    freq = pd.infer_freq(turnover.index)
    turnover_title = turnover_title or f"{turnover_rolling_period}-period rolling {freq}-freq Turnover"
    qis.plot_time_series(df=turnover,
                         var_format='{:,.2%}',
                         # y_limits=(0.0, None),
                         legend_stats=qis.LegendStats.AVG_NONNAN_LAST,
                         title=turnover_title,
                         ax=ax,
                         **kwargs)
    qis.add_bnb_regime_shadows(ax=ax, pivot_prices=pivot_prices, regime_params=regime_params)
    qis.set_spines(ax=ax, bottom_spine=False, left_spine=False)

    # costs
    ax = fig.add_subplot(gs[10:12, :2])
    costs = portfolio_data.get_costs(time_period=time_period, roll_period=turnover_rolling_period)
    freq = pd.infer_freq(costs.index)
    costs_title = f"{turnover_rolling_period}-period rolling {freq}-freq Costs"
    qis.plot_time_series(df=costs,
                         var_format='{:,.2%}',
                         # y_limits=(0.0, None),
                         legend_stats=qis.LegendStats.AVG_NONNAN_LAST,
                         title=costs_title,
                         ax=ax,
                         **kwargs)
    qis.add_bnb_regime_shadows(ax=ax, pivot_prices=pivot_prices, regime_params=regime_params)
    qis.set_spines(ax=ax, bottom_spine=False, left_spine=False)

    # constituents
    ax = fig.add_subplot(gs[12:, :2])
    num_investable_instruments = portfolio_data.get_num_investable_instruments(time_period=time_period)
    qis.plot_time_series(df=num_investable_instruments,
                         var_format='{:,.0f}',
                         legend_stats=qis.LegendStats.FIRST_AVG_LAST,
                         title='Number of investable and invested instruments',
                         ax=ax,
                         **kwargs)
    qis.add_bnb_regime_shadows(ax=ax, pivot_prices=pivot_prices, regime_params=regime_params)
    qis.set_spines(ax=ax, bottom_spine=False, left_spine=False)

    # ra perf table
    if add_all_benchmarks_to_nav_figure:
        benchmark_price = benchmark_prices
    else:
        benchmark_price = benchmark_prices[regime_benchmark]
    if is_grouped:
        ax = fig.add_subplot(gs[:2, 2:])
        portfolio_data.plot_ra_perf_table(ax=ax,
                                          benchmark_price=benchmark_price,
                                          time_period=time_period,
                                          perf_params=perf_params,
                                          is_grouped=is_grouped,
                                          **qis.update_kwargs(kwargs, dict(fontsize=fontsize)))
    else:  # plot two tables

        ax = fig.add_subplot(gs[0, 2:])
        portfolio_data.plot_ra_perf_table(ax=ax,
                                          benchmark_price=benchmark_price,
                                          time_period=time_period,
                                          perf_params=perf_params,
                                          is_grouped=is_grouped,
                                          **qis.update_kwargs(kwargs, dict(fontsize=fontsize)))
        ax = fig.add_subplot(gs[1, 2:])
        # change regression to weekly
        time_period1 = qis.get_time_period_shifted_by_years(time_period=time_period)
        if pd.infer_freq(benchmark_prices.index) in ['B', 'D']:
            local_kwargs = qis.update_kwargs(kwargs, dict(time_period=time_period1, alpha_an_factor=52, freq_reg='W-WED', fontsize=fontsize))
        else:
            local_kwargs = qis.update_kwargs(kwargs, dict(time_period=time_period1, fontsize=fontsize))
        portfolio_data.plot_ra_perf_table(ax=ax,
                                          benchmark_price=benchmark_price,
                                          perf_params=perf_params,
                                          is_grouped=is_grouped,
                                          **local_kwargs)

    # heatmap
    ax = fig.add_subplot(gs[2:4, 2:])
    portfolio_data.plot_monthly_returns_heatmap(ax=ax,
                                                time_period=time_period,
                                                title='Monthly Returns',
                                                **qis.update_kwargs(kwargs, dict(fontsize=fontsize, date_format='%Y')))

    # periodic returns
    ax = fig.add_subplot(gs[4:6, 2:])
    local_kwargs = qis.update_kwargs(kwargs=kwargs,
                                     new_kwargs=dict(fontsize=fontsize, square=False, x_rotation=90, transpose=True))
    portfolio_data.plot_periodic_returns(benchmark_prices=benchmark_prices,
                                         is_grouped=is_grouped,
                                         time_period=time_period,
                                         ax=ax,
                                         **local_kwargs)

    # perf contributors
    ax = fig.add_subplot(gs[6:8, 2])
    portfolio_data.plot_contributors(ax=ax,
                                     time_period=time_period,
                                     title=f"Performance Contributors {time_period.to_str()}",
                                     **kwargs)

    ax = fig.add_subplot(gs[6:8, 3])
    time_period_1y = qis.get_time_period_shifted_by_years(time_period=time_period)
    portfolio_data.plot_contributors(ax=ax,
                                     time_period=time_period_1y,
                                     title=f"Performance Contributors {time_period_1y.to_str()}",
                                     **kwargs)

    # regime data
    ax = fig.add_subplot(gs[8:10, 2:])
    portfolio_data.plot_regime_data(is_grouped=is_grouped,
                                    benchmark_price=benchmark_prices[regime_benchmark],
                                    time_period=time_period,
                                    perf_params=perf_params,
                                    regime_params=regime_params,
                                    ax=ax,
                                    **kwargs)

    local_kwargs = qis.update_kwargs(kwargs=kwargs, new_kwargs=dict(legend_loc=None))
    portfolio_data.plot_performance_attribution(time_period=time_period,
                                                attribution_metric=qis.AttributionMetric.PNL,
                                                ax=fig.add_subplot(gs[10:12, 2:]),
                                                **local_kwargs)

    portfolio_data.plot_performance_attribution(time_period=time_period,
                                                attribution_metric=qis.AttributionMetric.PNL_RISK,
                                                ax=fig.add_subplot(gs[12:, 2:]),
                                                **local_kwargs)

    figs = [fig]

    if add_var_risk_sheet:
        fig = plt.figure(figsize=figsize, constrained_layout=True)
        fig.suptitle(f"{portfolio_data.nav.name} var and risk profile", fontweight="bold", fontsize=8, color='blue')
        figs.append(fig)
        gs = fig.add_gridspec(nrows=14, ncols=4, wspace=0.0, hspace=0.0)

        # benchmark betas
        ax = fig.add_subplot(gs[:2, :2])
        factor_exposures = portfolio_data.compute_portfolio_benchmark_betas(benchmark_prices=benchmark_prices,
                                                                            time_period=time_period,
                                                                            beta_freq=beta_freq,
                                                                            factor_beta_span=factor_beta_span
                                                                            )
        factor_beta_title = factor_beta_title or f"Rolling {factor_beta_span}-period beta of {beta_freq}-freq returns"
        qis.plot_time_series(df=factor_exposures,
                             var_format='{:,.2f}',
                             legend_stats=qis.LegendStats.AVG_NONNAN_LAST,
                             title=factor_beta_title,
                             ax=ax,
                             **kwargs)
        qis.add_bnb_regime_shadows(ax=ax, pivot_prices=pivot_prices, regime_params=regime_params)
        qis.set_spines(ax=ax, bottom_spine=False, left_spine=False)

        # attribution
        ax = fig.add_subplot(gs[2:4, :2])
        factor_attribution = portfolio_data.compute_portfolio_benchmark_attribution(benchmark_prices=benchmark_prices,
                                                                                    beta_freq=beta_freq,
                                                                                    factor_beta_span=factor_beta_span,
                                                                                    time_period=time_period)
        factor_attribution_title = factor_attribution_title or f"Cumulative return attribution using rolling " \
                                                               f"{factor_beta_span}-period beta of {beta_freq}-freq returns"
        qis.plot_time_series(df=factor_attribution.cumsum(0),
                             var_format='{:,.0%}',
                             legend_stats=qis.LegendStats.LAST_NONNAN,
                             title=factor_attribution_title,
                             ax=ax,
                             **kwargs)
        qis.add_bnb_regime_shadows(ax=ax, pivot_prices=pivot_prices, regime_params=regime_params)
        qis.set_spines(ax=ax, bottom_spine=False, left_spine=False)

        # returns scatter
        ax = fig.add_subplot(gs[0:2, 2:])
        portfolio_data.plot_returns_scatter(ax=ax,
                                            benchmark_price=benchmark_prices.iloc[:, 0],
                                            time_period=time_period,
                                            freq=regime_params.freq,
                                            **kwargs)

        if len(benchmark_prices.columns) > 1:
            ax = fig.add_subplot(gs[2:4, 2:])
            portfolio_data.plot_returns_scatter(ax=ax,
                                                benchmark_price=benchmark_prices.iloc[:, 1],
                                                time_period=time_period,
                                                freq=regime_params.freq,
                                                **kwargs)

        # var
        ax = fig.add_subplot(gs[4:6, :2])
        portfolio_data.plot_portfolio_grouped_var(ax=ax,
                                                  is_correlated=True,
                                                  time_period=time_period,
                                                  **kwargs)
        qis.add_bnb_regime_shadows(ax=ax, pivot_prices=pivot_prices, regime_params=regime_params)
        qis.set_spines(ax=ax, bottom_spine=False, left_spine=False)
        ax = fig.add_subplot(gs[4:6, 2:])
        portfolio_data.plot_portfolio_grouped_var(ax=ax,
                                                  is_correlated=False,
                                                  time_period=time_period,
                                                  **kwargs)
        qis.add_bnb_regime_shadows(ax=ax, pivot_prices=pivot_prices, regime_params=regime_params)
        qis.set_spines(ax=ax, bottom_spine=False, left_spine=False)

        # vol regime data
        ax = fig.add_subplot(gs[6:8, :2])
        portfolio_data.plot_vol_regimes(ax=ax,
                                        benchmark_price=benchmark_prices.iloc[:, 0],
                                        time_period=time_period,
                                        freq=regime_params.freq,
                                        regime_params=regime_params,
                                        **kwargs)
        if len(benchmark_prices.columns) > 1:
            ax = fig.add_subplot(gs[6:8, 2:])
            portfolio_data.plot_vol_regimes(ax=ax,
                                            benchmark_price=benchmark_prices.iloc[:, 1],
                                            time_period=time_period,
                                            freq=regime_params.freq,
                                            regime_params=regime_params,
                                            **kwargs)

    if add_grouped_exposures:
        if is_1y_exposures:
            time_period1 = qis.get_time_period_shifted_by_years(time_period=time_period)
        else:
            time_period1 = time_period
        grouped_exposures_agg, grouped_exposures_by_inst = portfolio_data.get_grouped_long_short_exposures(time_period=time_period1)
        nrows = len(grouped_exposures_agg.keys())
        fig1 = plt.figure(figsize=figsize, constrained_layout=True)
        figs.append(fig1)
        fig1.suptitle(f"{portfolio_data.nav.name} Exposures by groups for period {time_period1.to_str()}",
                     fontweight="bold", fontsize=8, color='blue')
        gs = fig1.add_gridspec(nrows=nrows, ncols=2, wspace=0.0, hspace=0.0)
        local_kwargs = qis.update_kwargs(kwargs=kwargs, new_kwargs=dict(framealpha=0.9))
        for idx, (group, exposures_agg) in enumerate(grouped_exposures_agg.items()):
            datas = {f"{group} aggregated": grouped_exposures_agg[group],
                     f"{group} by instrument": grouped_exposures_by_inst[group]}
            for idx_, (key, df) in enumerate(datas.items()):
                ax = fig1.add_subplot(gs[idx, idx_])
                qis.plot_time_series(df=df,
                                     var_format='{:,.0%}',
                                     legend_stats=qis.LegendStats.AVG_MIN_MAX_LAST,
                                     title=f"{key}",
                                     ax=ax,
                                     **local_kwargs)
                qis.add_bnb_regime_shadows(ax=ax, pivot_prices=pivot_prices, regime_params=regime_params)
                qis.set_spines(ax=ax, bottom_spine=False, left_spine=False)
                ax.axhline(0, color='black', linewidth=0.5)

    if add_grouped_cum_pnl:
        if is_1y_exposures:
            time_period1 = qis.get_time_period_shifted_by_years(time_period=time_period)
        else:
            time_period1 = time_period
        grouped_pnls_agg, grouped_pnls_by_inst = portfolio_data.get_grouped_cum_pnls(time_period=time_period1)
        nrows = len(grouped_pnls_agg.keys())
        fig1 = plt.figure(figsize=figsize, constrained_layout=True)
        figs.append(fig1)
        fig1.suptitle(f"{portfolio_data.nav.name} P&L by groups for period {time_period1.to_str()}",
                     fontweight="bold", fontsize=8, color='blue')
        gs = fig1.add_gridspec(nrows=nrows, ncols=2, wspace=0.0, hspace=0.0)
        local_kwargs = qis.update_kwargs(kwargs=kwargs, new_kwargs=dict(framealpha=0.9))
        for idx, (group, pnls_agg) in enumerate(grouped_pnls_agg.items()):
            datas = {f"{group} aggregated": grouped_pnls_agg[group],
                     f"{group} by instrument": grouped_pnls_by_inst[group]}
            for idx_, (key, df) in enumerate(datas.items()):
                ax = fig1.add_subplot(gs[idx, idx_])
                qis.plot_time_series(df=df,
                                     var_format='{:,.0%}',
                                     legend_stats=qis.LegendStats.LAST_NONNAN,
                                     title=f"{key}",
                                     ax=ax,
                                     **local_kwargs)
                qis.add_bnb_regime_shadows(ax=ax, pivot_prices=time_period1.locate(pivot_prices),
                                           regime_params=BenchmarkReturnsQuantileRegimeSpecs(freq='ME'))
                qis.set_spines(ax=ax, bottom_spine=False, left_spine=False)

    return figs

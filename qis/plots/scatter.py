"""
scatter plot core
"""
# built in
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import scipy.stats as stats
from statsmodels import api as sm
from typing import Union, List, Tuple, Optional
from enum import Enum

# qis
import qis.plots as qp
import qis.utils as qu


def plot_scatter(df: pd.DataFrame,
                 x_column: str = None,
                 y_column: str = None,
                 hue: str = None,
                 xlabel: Union[str, bool, None] = True,
                 ylabel: Union[str, bool, None] = True,
                 title: Optional[str] = None,
                 annotation_labels: List[str] = None,
                 annotation_colors: List[str] = None,
                 annotation_color: Optional[str] = 'red',
                 add_universe_model_label: bool = True,
                 add_universe_model_prediction: bool = False,
                 add_universe_model_ci: bool = False,
                 add_hue_model_label: Optional[bool] = None,  # add hue eqs for data with hue
                 ci: Optional[int] = None,
                 order: int = 2,  # regression order
                 full_sample_order: Optional[int] = 2,  # full sample order can be different
                 fit_intercept: bool = True,
                 color0: str = 'darkblue',
                 colors: List[str] = None,
                 xvar_format: str = '{:.0%}',
                 yvar_format: str = '{:.0%}',
                 x_limits: Tuple[Optional[float], Optional[float]] = None,
                 y_limits: Tuple[Optional[float], Optional[float]] = None,
                 xticks: List[str] = None,
                 fontsize: int = 10,
                 linewidth: float = 1.5,
                 markersize: int = 4,
                 full_sample_label: str = 'Full sample: ',
                 add_45line: bool = False,
                 r2_only: bool = False,
                 legend_loc: str = 'upper left',
                 value_name: str = 'value_name',
                 ax: plt.Subplot = None,
                 **kwargs
                 ) -> plt.Figure:
    """
    x-y scatter of df
    """
    df = df.copy().dropna()

    if x_column is None:
        if len(df.columns) == 2 or (len(df.columns) == 3 and hue is not None):
            x_column = df.columns[0]
        else:
            raise ValueError(f"x_column is not defined for more than on columns")
    if y_column is None:
        if len(df.columns) == 2 or (len(df.columns) == 3 and hue is not None):  # x and y
            y_column = df.columns[1]
        else:  # melting to column value_name with hue = all columns ba t x
            hue = 'hue'
            y_column = value_name
            df = pd.melt(df, id_vars=[x_column], value_vars=df.columns.drop(x_column), var_name=hue,
                         value_name=value_name)

    if hue is not None and add_hue_model_label is None:  # override to true unless false
        add_hue_model_label = True

    if ax is None:
        fig, ax = plt.subplots(1, 1, figsize=(8, 6))
    else:
        fig = None

    estimated_reg_models = {}
    if hue is not None:
        if colors is None:
            colors = qp.get_n_colors(n=len(df[hue].unique()), **kwargs)
        palette = colors

        hue_ids = df[hue].unique()
        for idx, hue_id in enumerate(hue_ids):
            # estimate model equation
            data_hue = df[df[hue] == hue_id].sort_values(by=x_column)
            x = data_hue[x_column].to_numpy()
            y = data_hue[y_column].to_numpy()
            x1 = qu.get_ols_x(x=x, order=order, fit_intercept=fit_intercept)
            reg_model = sm.OLS(y, x1).fit()
            estimated_reg_models[hue_id] = reg_model

            # plot data points
            sns.scatterplot(x=x_column, y=y_column, data=data_hue, color=palette[idx], s=markersize, ax=ax)

            if order > 0:  # plot prediction
                if ci is not None: # not possible to control reg equation in regplot, only use for ci
                    sns.regplot(x=x_column, y=y_column, data=data_hue,
                                ci=ci,
                                order=order, truncate=True,
                                color=palette[idx],
                                scatter_kws={'s': markersize},
                                line_kws={'linewidth': linewidth},
                                ax=ax)
                else:
                    prediction = reg_model.predict(x1)
                    ax.plot(x, prediction, color=palette[idx], lw=linewidth, linestyle='-')

    else:
        if full_sample_order is None:
            pass
        elif full_sample_order == 0:  # just scatter plot
            sns.scatterplot(x=x_column, y=y_column, data=df,
                            # ci=ci,
                            s=markersize, color=color0, ax=ax)
        else:  # regplot add scatter and ml lines even if order is == 0
            sns.regplot(x=x_column, y=y_column, data=df, ci=ci, order=full_sample_order, color=color0,
                        scatter_kws={'s': markersize},
                        line_kws={'linewidth': linewidth}, ax=ax)

    # add ml equations to labels
    legend_labels = []
    legend_colors = []
    if full_sample_order is not None:
        if (add_universe_model_prediction or add_universe_model_label or add_universe_model_ci) and full_sample_order > 0:
            xy = df[[x_column, y_column]].sort_values(by=x_column)
            x = xy[x_column].to_numpy()
            y = xy[y_column].to_numpy()
            x1 = qu.get_ols_x(x=x, order=full_sample_order, fit_intercept=fit_intercept)
            reg_model = sm.OLS(y, x1).fit()

            if add_universe_model_prediction:
                prediction = reg_model.predict(x1)
                ax.plot(x, prediction, color=color0, lw=linewidth, linestyle='--')

            if add_universe_model_ci:
                y_model = reg_model.predict(x1)
                ci = calc_ci(x=x, y=y, y_model=y_model)
                # ax.fill_between(x, y + ci, y - ci, color="None", linestyle="--")
                ax.plot(x, y_model - ci, "--", color="0.5")
                ax.plot(x, y_model + ci, "--", color="0.5")

            if add_universe_model_label:
                text_str = f"{full_sample_label} " \
                           f"{qu.reg_model_params_to_str(reg_model=reg_model, order=full_sample_order, r2_only=False, fit_intercept=fit_intercept, **kwargs)}"
                legend_labels.append(text_str)
                legend_colors.append(color0)

    # add colors for annotation labels
    df['color'] = color0
    if hue is not None :
        hue_ids = df[hue].unique()
        for color, hue_id in zip(colors, hue_ids):
            df.loc[df[hue] == hue_id, 'color'] = 'red'  # ad color for hue
            if order > 0:
                if add_hue_model_label:
                    reg_model = estimated_reg_models[hue_id]
                    text_str = (f"{hue_id}: " 
                                f"{qu.reg_model_params_to_str(reg_model=reg_model, order=order, r2_only=r2_only, fit_intercept=fit_intercept, **kwargs)}")
                else:
                    text_str = hue_id
                legend_labels.append(text_str)
            else:
                legend_labels.append(hue_id)
            legend_colors.append(color)

    elif hue is not None and order == 0:
        legend_labels = df[hue].unique()
        legend_colors = colors

    # add labels
    if annotation_labels is not None:
        if annotation_colors is not None:
            colors = annotation_colors
        elif annotation_color is not None:
            colors = len(df.index) * [annotation_color]
        else:
            colors = df['color']
        for label, x, y, color in zip(annotation_labels, df[x_column], df[y_column], colors):
            ax.annotate(label,
                        xy=(x, y), xytext=(1, 1),
                        textcoords='offset points', ha='left', va='bottom',
                        color=color,
                        fontsize=fontsize)
            if label != '':
                ax.scatter(x=x, y=y, c=color, s=20)

    if add_45line:  # make equal:
        ymin, ymax = ax.get_ylim()
        xmin, xmax = ax.get_xlim()
        min = ymin if ymin < xmin else xmin
        max = ymax if ymax > xmax else xmax
        ax.set_xlim([min, max])
        ax.set_ylim([min, max])
        x = np.linspace(*ax.get_xlim())
        ax.plot(x, x, color='black', lw=1, linestyle='--')

    if x_limits is not None:
        qp.set_x_limits(ax=ax, x_limits=x_limits)
    if y_limits is not None:
        qp.set_y_limits(ax=ax, y_limits=y_limits)

    if xticks is not None:
        qp.set_ax_tick_labels(ax=ax, x_rotation=0, xticks=df[x_column].to_numpy(), x_labels=xticks,
                               fontsize=fontsize)
    else:
        qp.set_ax_tick_labels(ax=ax, x_rotation=0, fontsize=fontsize)

    if isinstance(xlabel, bool):
        if xlabel is True:
            xlabel = 'x = ' + x_column
        else:
            xlabel = ''
    if isinstance(ylabel, bool):
        if ylabel is True:
            ylabel = 'y = ' + y_column
        else:
            ylabel = ''
    qp.set_ax_xy_labels(ax=ax, xlabel=xlabel, ylabel=ylabel, fontsize=fontsize, **kwargs)

    qp.set_ax_ticks_format(ax=ax, xvar_format=xvar_format, yvar_format=yvar_format, fontsize=fontsize, **kwargs)

    qp.set_legend(ax=ax,
                  labels=legend_labels,
                  colors=legend_colors,
                  legend_loc=legend_loc,
                  fontsize=fontsize,
                  **kwargs)

    if title is not None:
        qp.set_title(ax=ax, title=title, fontsize=fontsize, **kwargs)

    qp.set_spines(ax=ax, **kwargs)

    return fig


def plot_classification_scatter(df: pd.DataFrame,
                                x_column: Optional[str] = None,
                                y_column: Optional[str] = None,
                                hue_name: str = 'hue',
                                num_buckets: Optional[int] = None,
                                bins: np.ndarray = np.array([-3.0, -1.5, 0.0, 1.5, 3.0]),
                                order: int = 1,
                                title: str = None,
                                full_sample_order: Optional[int] = 3,
                                markersize: int = 10,
                                xvar_format: str = '{:.2f}',
                                yvar_format: str = '{:.2f}',
                                fit_intercept: bool = False,
                                ax: plt.Subplot = None,
                                **kwargs
                                ) -> Optional[plt.Figure]:
    """
    add bin classification using x_column
    """
    if x_column is None:
        if len(df.columns) == 2:
            x_column = df.columns[0]
        else:
            raise ValueError(f"x_column is not defined for more than on columns")
    if y_column is None:
        if len(df.columns) == 2:  # x and y
            y_column = df.columns[1]
        else:
            raise ValueError(f"y_column is not defined for more than on columns")

    df, _ = qu.add_quantile_classification(df=df, x_column=x_column, hue_name=hue_name, num_buckets=num_buckets, bins=bins)

    fig = plot_scatter(df=df,
                       x_column=x_column,
                       y_column=y_column,
                       hue=hue_name,
                       fit_intercept=fit_intercept,
                       title=title,
                       order=order,
                       full_sample_order=full_sample_order,
                       markersize=markersize,
                       xvar_format=xvar_format,
                       yvar_format=yvar_format,
                       add_universe_model_ci=False,
                       add_hue_model_label=True,
                       ax=ax,
                       **kwargs)
    return fig


def calc_ci(x: np.ndarray, y: np.ndarray, y_model: np.ndarray) -> np.ndarray:
    n = x.shape[0]
    m = 2
    dof = n - m
    t = stats.t.ppf(0.95, dof)
    #x2 = np.linspace(np.min(x), np.max(x), 100)

    # Estimates of Error in Data/Model
    resid = y - y_model
    # chi2 = np.sum((resid / y_model) ** 2)  # chi-squared; estimates error in data
    # chi2_red = chi2 / dof  # reduced chi-squared; measures goodness of fit
    s_err = np.sqrt(np.sum(resid ** 2) / dof)  # standard deviation of the error

    ci = t * s_err * np.sqrt(1 / n + (x - np.mean(x)) ** 2 / np.sum((x - np.mean(x)) ** 2))
    return ci


def get_random_data(is_random_beta: bool = True,
                    n: int = 10000
                    ) -> pd.DataFrame:

    x = np.random.normal(0.0, 1.0, n)
    eps = np.random.normal(0.0, 1.0, n)
    if is_random_beta:
        beta = np.random.normal(1.0, 1.0, n)*np.square(x)
    else:
        beta = np.ones(n)
    y = beta*x + eps
    df = pd.concat([pd.Series(x, name='x'), pd.Series(y, name='y')], axis=1)
    df = df.sort_values(by='x', axis=0)

    return df


class UnitTests(Enum):
    SCATTER = 1
    CLASSIFICATION_SCATTER = 2


def run_unit_test(unit_test: UnitTests):

    np.random.seed(2)
    df = get_random_data(n=100000)
    print(df)

    if unit_test == UnitTests.SCATTER:
        plot_scatter(df=df)

    elif unit_test == UnitTests.CLASSIFICATION_SCATTER:
        plot_classification_scatter(df=df, x_column='x', y_column='y')

    plt.show()


if __name__ == '__main__':

    unit_test = UnitTests.SCATTER

    is_run_all_tests = False
    if is_run_all_tests:
        for unit_test in UnitTests:
            run_unit_test(unit_test=unit_test)
    else:
        run_unit_test(unit_test=unit_test)

import datetime
import os
from Utils.lib import xlsxwriter

__author__ = "Braulio Ríos"


# Generate an excel file with one time column, and one (or two) data columns, and plot the result.
def plot_signals(file_name, x_vector, y_vector_1, y_legend_1, y_vector_2=None, y_legend_2=None, x_label='Time (s)',
                 y_label='Voltage (V)', title="Signal Data"):
    if len(x_vector) != len(y_vector_1):
        raise RuntimeError("Unable to Plot. X and Y lengths are different (%d - %d)" % (len(x_vector), len(y_vector_1)))
    if (y_vector_2 is not None) and (len(y_vector_2) != len(y_vector_1)):
        raise RuntimeError("Unable to Plot the two given signals. "
                           "Y1 and Y2 lengths are different (%d - %d)" % (len(x_vector), len(y_vector_1)))
    # Excel file and worksheet
    workbook = xlsxwriter.Workbook(file_name)
    worksheet = workbook.add_worksheet()
    bold = workbook.add_format({'bold': True})
    numeric = workbook.add_format({'num_format': '0.00'})
    # Titles
    worksheet.write('A1', title, bold)
    worksheet.write('A2', x_label, bold)
    worksheet.write('B2', y_legend_1, bold)
    if y_vector_2 is not None:
        worksheet.write('C2', y_legend_2, bold)
    # Add data columns
    worksheet.write_column('A3', x_vector, numeric)
    worksheet.write_column('B3', y_vector_1, numeric)
    if y_vector_2 is not None:
        worksheet.write_column('C3', y_vector_2, numeric)
    # Create Plot
    n_data = len(x_vector)
    plot = workbook.add_chart({'type': 'line'})
    plot.add_series({
                    'name':       y_legend_1,
                    'categories': ['Sheet1', 2, 0, 2 + n_data, 0],
                    'values':     ['Sheet1', 2, 1, 2 + n_data, 1],
                    })
    if y_vector_2 is not None:
        plot.add_series({
                        'name':       y_legend_2,
                        'categories': ['Sheet1', 2, 0, 2 + n_data, 0],
                        'values':     ['Sheet1', 2, 2, 2 + n_data, 2],
                        })
    # Add a chart title and some axis labels.
    plot.set_title ({'name': title})
    plot.set_x_axis({'name': x_label, 'num_format': '0'})
    plot.set_y_axis({'name': y_label, 'num_format': '0.00'})
    # Set an Excel chart style. Colors with white outline and shadow.
    plot.set_style(10)
    # Insert the chart into the worksheet (with an offset).
    worksheet.insert_chart('F3', plot)
    workbook.close()

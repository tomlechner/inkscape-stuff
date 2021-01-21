#!/usr/bin/env python

'''
columncalendar.py

A calendar generator plugin for Inkscape.

This is severely refactored from 2008 version to display a long
column of dates.

Copyright (C) 2015 Tom Lechner
Copyright (C) 2008 Aurelio A. Heckert <aurium(a)gmail.com>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA


TODO
- Multiple columns
- Better layout options for writing out month names
'''

__version__ = "0.3"


import inkex, simplestyle, re, calendar
from datetime import *
from lxml import etree


class ColumnCalendar (inkex.Effect):

    def __init__(self):
        inkex.Effect.__init__(self)

        self.arg_parser.add_argument("--tab",
          action="store", type=str,
          dest="tab")
        self.arg_parser.add_argument("--week-width",
          action="store", type=str,
          dest="week_width_str", default="2.5in",
          help="Width of a week. 0 means use 1/3 of document width.")
        self.arg_parser.add_argument("--month",
          action="store", type=int,
          dest="month", default=datetime.today().month,
          help="Month to be generated. If 0, then the current month will be generated.")
        self.arg_parser.add_argument("--year",
          action="store", type=int,
          dest="year", default=datetime.today().year,
          help="Year to be generated. If 0, then the current year will be generated.")

        self.arg_parser.add_argument("--fill-empty-day-boxes",
          action="store", type=bool,
          dest="fill_edb", default=False,
          help="Fill empty day boxes with next month days.")
        self.arg_parser.add_argument("--color-grid",
          action="store", type=str,
          dest="color_grid", default="#777",
          help='Color for the grid lines.')
        self.arg_parser.add_argument("--grid-lines",
          action="store", type=str,
          dest="grid_lines", default=".2pt",
          help='Grid line thickness')
        self.arg_parser.add_argument("--color-year",
          action="store", type=str,
          dest="color_year", default="#000",
          help='Color for the year header.')
        self.arg_parser.add_argument("--color-month",
          action="store", type=str,
          dest="color_month", default="#000",
          help='Color for the month name header.')
        self.arg_parser.add_argument("--color-day-name",
          action="store", type=str,
          dest="color_day_name", default="#999",
          help='Color for the week day names header.')
        self.arg_parser.add_argument("--color-day",
          action="store", type=str,
          dest="color_day", default="#000",
          help='Color for the common day box.')
        self.arg_parser.add_argument("--color-weekend",
          action="store", type=str,
          dest="color_weekend", default="#777",
          help='Color for the weekend days.')
        self.arg_parser.add_argument("--color-nmd",
          action="store", type=str,
          dest="color_nmd", default="#BBB",
          help='Color for the next month day, in enpty day boxes.')
        self.arg_parser.add_argument("--month-names",
          action="store", type=str,
          dest="month_names", default='January February March April May June '+\
                              'July August September October November December',
          help='The month names for localization.')
        self.arg_parser.add_argument("--day-names",
          action="store", type=str,
          dest="day_names", default='Sun Mon Tue Wed Thu Fri Sat',
          help='The week day names for localization.')

    def validate_options(self):
        #inkex.errormsg( self.options.input_encode )
        # Convert string names lists in real lists:
        m = re.match( '\s*(.*[^\s])\s*', self.options.month_names )
        self.options.month_names = re.split( '\s+', m.group(1) )

        m = re.match( '\s*(.*[^\s])\s*', self.options.day_names )
        self.options.day_names = re.split( '\s+', m.group(1) )

        # Validate names lists:
        if len(self.options.month_names) != 12:
          errormsg('The month name list "'+
                         str(self.options.month_names)+
                         '" is invalid. Using default.')
          self.options.month_names = ['January','February','March',
                                      'April',  'May',     'June',
                                      'July',   'August',  'September',
                                      'October','November','December']
        if len(self.options.day_names) != 7:
          inkex.errormsg('The day name list "'+
                         str(self.options.day_names)+
                         '" is invalid. Using default.')
          self.options.day_names = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat']

        # Convert year 0 to current year:
        if self.options.year == 0:  self.options.year  = datetime.today().year
        if self.options.month == 0: self.options.month = datetime.today().month



    def calculate_size_and_styles(self):

        #month_margin month_width months_per_line auto_organize
        self.doc_w = self.svg.unittouu(self.document.getroot().get('width'))
        self.doc_h = self.svg.unittouu(self.document.getroot().get('height'))

        self.pad = self.doc_w*.075


         #compute month width. A row of months fits to 80% of document width
        self.month_w = self.doc_w - 2*self.pad 
        self.month_h = self.doc_h - 2*self.pad
        self.options.week_width=self.svg.unittouu( self.options.week_width_str )
        if self.options.week_width <=0:
            self.options.week_width = float(self.document.getroot().get('width'))/3
        self.day_w = self.options.week_width / 7
        self.numweeks = int(self.month_h / self.day_w)
        if self.numweeks<=0: self.numweeks=1
        self.day_h = self.month_h/self.numweeks


        self.textheight=self.day_h*.3 #pts

        self.style_day = {
          'font-size': str( self.textheight),
          'font-family': 'arial',
          'text-anchor': 'middle',
          'fill': self.options.color_day
          }
        self.style_weekend = self.style_day.copy()
        self.style_weekend['fill'] = self.options.color_weekend
        self.style_weekend['text-anchor'] = 'start'

        self.style_nmd = self.style_day.copy()
        self.style_nmd['fill'] = self.options.color_nmd

        self.style_month = self.style_day.copy()
        self.style_month['fill'] = self.options.color_month
        self.style_month['font-size'] = str( self.textheight*1.25 )

        self.style_day_name = self.style_day.copy()
        self.style_day_name['fill'] = self.options.color_day_name
        self.style_day_name['font-size'] = str( self.day_w / 3 )

        self.style_year = self.style_day.copy()
        self.style_year['fill'] = self.options.color_year
        self.style_year['font-size'] = str( self.textheight * 2 )
        self.style_year['font-weight'] = 'bold'

        self.line_style = {
                'stroke': self.options.color_grid, #"#000000",
                'fill':   "none",
                'stroke-width': self.options.grid_lines, #".5pt",
                'stroke-linecap' : "round"
            }


    def RenderMonthGrid(self, month, year):
        textheight = self.textheight

        calendar.setfirstweekday(calendar.SUNDAY)
        cal = calendar.monthcalendar(year,month)
        parent = self.year_g

        monthw = self.month_w
        monthh = self.month_h
        dayw = self.day_w
        dayh = self.day_h

        week_x = self.doc_w/2 - self.options.week_width/2
        week_y = self.pad

        #
        #   s m t w t f s
        #
        #



        txt_atts = { 'id': 'month' } #group for month day text
        self.month_g = etree.SubElement(parent, 'g', txt_atts)


         #horizontal lines
        y=week_y
        for week in range(self.numweeks):
            if week==0:
                 #Add initial horizontal at top
                path="M " + str(week_x)+","+str(week_y) + "L "+str(week_x+self.options.week_width)+","+str(week_y)
                line_atts = {'style': str(inkex.Style(self.line_style)), # simplestyle.formatStyle(self.line_style),
                             'd': path
                            }
                etree.SubElement(parent, 'path', line_atts)

             #Add horizontal at bottom of each line
            path="M " + str(week_x)+","+str(y+self.day_h) + "L "+str(week_x+self.options.week_width)+","+str(y+self.day_h)
            line_atts = {'style': str(inkex.Style(self.line_style)),
                         'd': path
                        }
            etree.SubElement(parent, 'path', line_atts)
            y=y+dayh

         #vertical lines
        x=week_x
        for c in range(8):
            path="M " + str(x)+","+str(week_y) + "L "+str(x)+","+str(week_y+self.doc_h-2*self.pad)
            line_atts = {'style': str(inkex.Style(self.line_style)),
                         'd': path
                        }
            etree.SubElement(parent, 'path', line_atts)
            x += dayw

         #write year on top
        txt_atts = {
          'x': str( week_x ),
          'y': str( week_y-textheight ),
          'id': str(year),
          'text-anchor': "start"
          }
        etree.SubElement(self.month_g, 'text', txt_atts).text = str(year)



        #text
        very_first = True
        first_week = True
        make_month = True
        curweek = 0
        month = month-1
        while week_y+dayh < self.doc_h-self.pad:
            if first_week and not very_first: first_week=False

            if make_month:
                make_month=False
                curweek=0
                month=month+1
                if month==13:
                    month=1
                    year = year+1
                cal = calendar.monthcalendar(year,month)

            if curweek==len(cal):
                curweek=0
                make_month=True
                continue

            week=cal[curweek]

            x = week_x + textheight/4
            y = week_y
            i = 0
            while i<7:
                day=week[i]

                i=i+1
                if (day==0 and first_week):
                    x += dayw
                    continue

                txt_atts = {
                  'x': str( x ),
                  'y': str( week_y+textheight ),
                  'id': str(year)+"_"+str(month)+'_'+str(day),
                  'text-anchor': "start"
                  }
                if (i==1 or i==7): txt_atts['style'] = str(inkex.Style(self.style_weekend))



                if day==1 or very_first:
                     #write month then day
                    txt_atts = {
                      'x': str( x ),
                      'y': str( week_y+textheight ),
                      'font-size': str( self.textheight*.6),
                      'id': str(year)+"_"+str(month)+'_'+str(day),
                      'text-anchor': "start"
                      }
                    etree.SubElement(self.month_g, 'text', txt_atts).text = self.options.month_names[month-1]

                    txt_atts = {
                      'x': str( x ),
                      'y': str( week_y+2*textheight ),
                      'id': str(year)+"_"+str(month)+'_'+str(day),
                      'text-anchor': "start"
                      }
                    etree.SubElement(self.month_g, 'text', txt_atts).text = str(day)
                    very_first = False

                else:
                    if day==0:
                        if first_week: 
                            x += dayw
                            continue
                        month=month+1
                        curweek=0
                        if month==13:
                            month=1
                            year = year+1
                        cal = calendar.monthcalendar(year,month)
                        week=cal[0]
                        i -= 1
                        continue

                     #write day number only
                    etree.SubElement(self.month_g, 'text', txt_atts).text = str(day)

                x += dayw


            week_y += dayh;           
            curweek=curweek+1




    def effect(self):
        self.validate_options()
        self.calculate_size_and_styles()
        parent = self.document.getroot()

         #create whole group for everything
        txt_atts = {
          'id': 'year_'+str(self.options.year),
          'font-size': str(self.textheight)
          }
        self.year_g = etree.SubElement(parent, 'g', txt_atts)


        self.RenderMonthGrid(self.options.month, self.options.year)



if __name__ == '__main__':   #pragma: no cover
    e = ColumnCalendar()
    e.run()

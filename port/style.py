# This program is free software; you can redistribute it and/or modify 
# it under the terms of the GNU General Public License as published by 
# the Free Software Foundation; either version 2 of the License, or 
# (at your option) any later version. 
# 
# This program is distributed in the hope that it will be useful, 
# but WITHOUT ANY WARRANTY; without even the implied warranty of 
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the 
# GNU General Public License for more details. 
# 
# You should have received a copy of the GNU General Public License 
# along with this program; if not, write to the Free Software 
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA 

""" GUI look&feel related declarations """ 
from sugar.graphics import style 

def font_zoom(size):
    """ 21 Returns the proper font size for current Sugar environment
    NOTE: Use this function only if you are targeting activity for XO with 
    0.82 Sugar and want non-default font sizes, otherwise just
    do not mention font sizes in your code
    """

    if hasattr(style, '_XO_DPI'):
        return style.zoom(size)
    else:
        return size 
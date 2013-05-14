'''
Created on 28.04.2013

@author: H
'''



def draw_arrow(dc, fr, to, tail_angle, tail_length):
    """ fr, to are instances of Vectord2D class """
    end_x, end_y = to[0], to[1]
    vec = -(to - fr)
    vec = vec.normalized()
    tail_1 = vec.rotated(tail_angle) * tail_length
    tail_2 = vec.rotated(-tail_angle) * tail_length
    dc.DrawLine(end_x, end_y, end_x+tail_1[0], end_y+tail_1[1])
    dc.DrawLine(end_x, end_y, end_x+tail_2[0], end_y+tail_2[1])


def draw_text(dc, text, center_x, center_y):
    """ Draws text, given text center """
    tw, th = dc.GetTextExtent(text)
    dc.DrawText(text, (center_x-tw/2),  (center_y-th/2))
    
def draw_text_lb_corner(dc, text, pos_x, pos_y, size_multiplier=1):
    """ Draws text, given the left bottom point """
    tw, th = dc.GetTextExtent(text, size_multiplier)
    dc.DrawText(text, (pos_x-tw),  (pos_y-th), size_multiplier=size_multiplier)
    
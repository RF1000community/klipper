#!/usr/bin/gnuplot -p
# Recv: // Fit result: m = 0.000106, b = -0.998612, r = 0.992333, sm = 0.000008, sb = 0.000980

set title "Load cell probe fit" font "sans,18"

set style line 1 lc rgb 'red' lt 1 lw 2
set style line 2 lc rgb 'black' lt 0 lw 1

set xlabel "Z [mm]"
set ylabel "force [digits]"

set key at -0.98,-250

set arrow 1 from -0.998612,-300 to -0.998612,50 nohead lt 0

plot [-1.032:-0.977] 'lc-probe-measurement.txt' title "measurement",        \
     [-1.027:-0.998] (x + 0.998612)/0.000106 title "fit" with line ls 1, \
     [-1.032:0] 0 notitle with line ls 2

set terminal svg
set output "lc-probe-measurement.svg"
replot

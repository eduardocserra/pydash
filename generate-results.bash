#!/bin/bash

# variable w e buffer_min
for i in 0.1 0.3 0.35 0.45 0.5 0.6; do
    for j in 13 20 26 35 50; do
        python main.py $i $j True
        mkdir results-w-$i-bmin-$j
        cp -r results/* results-w-$i-bmin-$j
        echo "w=$i b_min=$j k=0.14 E=0.15 alfa=0.2 beta=0.2" >> results-w-$i-bmin-$j/parameter.txt
    done
done
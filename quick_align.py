#!/usr/bin/env python

import sys
import csv
import pysam
import parasail
import argparse
import textwrap as tw

def get_sequence(file):
    fasta = pysam.FastxFile(file)
    reference = None
    for record in fasta:
        # For this narrow application there should be exactly one entry in the reference file
        assert(reference is None)
        reference = record
    return reference

def get_alignment_parasail(reference_genome, input_genome):
    
    # the dna full matrix supports ambiguity codes, although "N"s are not given free mismatches as we might like
    # the alignments appear good enough for our purpose however
    # do not penalise gaps at end of database
    result = parasail.sg_dx_trace_striped_32(input_genome.sequence, reference_genome.sequence, 10, 1, parasail.dnafull)
    traceback = result.traceback

    return traceback.ref, traceback.comp, traceback.query

def alignment2vcf(reference_name, reference_aligned, query_aligned):

    print("##fileformat=VCFv4.2")
    print('##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">')
    print("##contig=<ID=%s>" % (reference_name)
    print("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tsample")


    # only write out out records for overlapping region
    q_start = len(query_aligned) - len(query_aligned.lstrip('-'))
    q_end = len(query_aligned) - (len(query_aligned) - len(query_aligned.rstrip('-')))

    i = q_start
    query_position = q_start
    reference_position = q_start
    n = q_end

    while i < n:
        if query_aligned[i] == reference_aligned[i]:
            reference_position += 1
            query_position += 1
            i += 1
        else:
            # new difference found, find the next matching base
            j = i
            while j < n and query_aligned[j] != reference_aligned[j]:
                j += 1

            # Get difference strings
            q_sub = query_aligned[i:j]
            r_sub = reference_aligned[i:j]

            q_gaps = q_sub.count("-")
            r_gaps = r_sub.count("-")

            offset = 0
            if q_gaps > 0 or r_gaps > 0:
                # append a single base to the start
                q_sub = query_aligned[i-1] + q_sub.replace("-", "")
                r_sub = reference_aligned[i-1] + r_sub.replace("-", "")
                offset = 1

            # Record the difference
            print("%s\t%d\t.\t%s\t%s\t.\t.\t.\tGT\t1" % (reference_name, reference_position - offset + 1, r_sub.upper(), q_sub.upper()))

            # update counters
            reference_position += (j - i - r_gaps)
            query_position += (j - i - q_gaps)
            i = j


def main():
    """
    Main method for script
    """
    description = 'Align a pair of genomes and write the results in various formats'
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-g', '--genome', help='consensus genome FASTA file to process')
    parser.add_argument('-r', '--reference-genome', help='fasta file containing the reference genome')
    parser.add_argument('-o', '--output-mode', default="differences")

    if len(sys.argv) <= 1:
        parser.print_help(sys.stderr)
        sys.exit(1)
    args = parser.parse_args()

    reference_genome = get_sequence(file=args.reference_genome)
    input_genome = get_sequence(file=args.genome)
    (reference_aligned, comparison_aligned, query_aligned) = get_alignment_parasail(reference_genome, input_genome)

    if args.output_mode == "differences":
        columns = 120
        for start in range(0, len(reference_aligned), columns):

            r = reference_aligned[start:start+columns]
            c = comparison_aligned[start:start+columns]
            q = query_aligned[start:start+columns]

            if r != q:
                print(start, r)
                print(start, c)
                print(start, q)
                print()
    elif args.output_mode == "tabular":
        print("reference\tquery")
        print("%s\t%s" % (reference_aligned, query_aligned))
    elif args.output_mode == "vcf":
        alignment2vcf(reference_genome.name, reference_aligned, query_aligned)

if __name__ == '__main__':
    main()

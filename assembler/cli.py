import click
import time
import os.path
import sys

from assembler.rebuilder import AnchorBuilder
from assembler.handler import Orchestrator
from assembler.builder import AnchorDictionary
import assembler.qc
import assembler.helpers


@click.group()
def cli():
    """Anchor processing tool for the assembler package."""
    pass

@cli.command()
@click.option(
    "--graph",
    required=True,
    type=click.Path(exists=True),
    help="Input packedgraph file (.vg)",
)
@click.option(
    "--index",
    required=True,
    type=click.Path(exists=True),
    help="Input distance index file (.dist)",
)
@click.option(
    "--output-prefix",
    required=True,
    type=click.Path(),
    help="Output prefix for the anchor dictionary",
)
@click.option(
    "--alignment",
    required=True,
    type=click.Path(exists=True),
    help="Input alignment file",
)

def get_anchors_from_reads(graph, index, output_prefix, alignment):
    output_dictionary = output_prefix + ".snarl_nodes.tsv"  # output TSV with snarl boundary as nodes and nodes inside it as a list

    """Identify leaf snarls in graph using SnarlDistanceIndex"""
    t0 = time.time()
    anchor_builder = AnchorBuilder(alignment)
    anchor_builder.build(graph, index)  # done
    anchor_builder.get_leaf_snarls_with_boundaries()    # done
    print(
        f"{len(anchor_builder.leaf_snarls)} leaf snarls and their boundaries computed in {time.time()-t0:.2f}s",
        flush=True,
        file=sys.stderr,
    )
    anchor_builder.dump_forward_reverse_snarl_boundaries_dict(output_prefix)
    if output_dictionary:
        anchor_builder.dump_snarl_dictionary(output_dictionary)


    """Identify anchors based on path taken by reads"""
    debug_file = output_prefix + ".debug_gaf_process.csv"                             # Not populating yet, but can add later
    reads_out_file = output_prefix + ".reads_processed.tsv"                           # TSV with info on all reads in the subregion. Helpful for debugging.
    anchor_reads_file = output_prefix + ".reads_with_anchors.tsv"                     # TSV with anchors and corresponding reads it's present in (not necessarily base level matched)
    anchor_bpmatched_reads_file = output_prefix + ".bpmatched_reads_with_anchors.tsv" # TSV with anchors and base-level matched reads only
    anchors_json_file = output_prefix + ".anchors.json"
    t1 = time.time()

    anchor_builder.process(debug_file, reads_out_file)

    with open(anchor_reads_file, "w") as arf:
        for anchor, read_info in anchor_builder.anchors_to_reads.items():
            print(
                f"{anchor}\t{read_info}",
                file=arf
            )
    print("Generated anchor_reads_file")

    anchor_builder.dump_bp_matched_reads()
    with open(anchor_bpmatched_reads_file, "w") as arf:
        for anchor, read_info in anchor_builder.anchors_to_bpmatched_reads.items():
            print(
                f"{anchor}\t{read_info}",
                file=arf
            )
    print("Generated anchor_bpmatched_reads_file")

    anchor_builder.dump_anchors_to_json_for_shasta(anchors_json_file)
    print("anchors JSON for shasta created!")


@cli.command()
@click.option(
    "--graph",
    required=True,
    type=click.Path(exists=True),
    help="Input packedgraph file (.vg)",
)
@click.option(
    "--index",
    required=True,
    type=click.Path(exists=True),
    help="Input distance index file (.dist)",
)
@click.option(
    "--output-prefix",
    required=True,
    type=click.Path(),
    help="Output prefix for the anchor dictionary",
)

def build(graph, index, output_prefix):
    output_dictionary = output_prefix + ".pkl"
    bandage_csv = output_prefix + ".bandage.csv"
    sizes_csv = output_prefix + ".sizes.tsv"
    paths_file = output_prefix + ".used_pathnames.txt"
    # positioned_dict = output_prefix + ".positioned.json"

    """Build an anchor dictionary from graph and index files."""
    t0 = time.time()
    dictionary_builder = AnchorDictionary()
    dictionary_builder.build(graph, index)
    dictionary_builder.fill_anchor_dictionary()
    print(
        f"Anchors dictionary from {len(dictionary_builder.leaf_snarls)} snarls, containing {len(dictionary_builder.sentinel_to_anchor)} sentinels built in {time.time()-t0:.2f}",
        flush=True,
        file=sys.stderr,
    )
    dictionary_builder.add_positions_to_anchors()
    dictionary_builder.dump_dictionary(output_dictionary)
    # dictionary_builder.print_anchor_boundaries_dict(output_prefix)
    if bandage_csv:
        dictionary_builder.print_sentinels_for_bandage(bandage_csv)

    if sizes_csv:
        dictionary_builder.print_dict_sizes(sizes_csv)
    
    # if paths_file:
    #     dictionary_builder.print_paths_used(paths_file)

    # if positioned_dict:
    #     dictionary_builder.generate_positioned_dictionary("", positioned_dict)

    click.echo(f"Anchor dictionary built and saved to {output_dictionary}")


@cli.command()
@click.option(
    "--dictionary",
    required=True,
    type=click.Path(exists=True),
    help="Input anchor dictionary file",
)
@click.option(
    "--graph", required=True, type=click.Path(exists=True), help="Input graph file"
)
@click.option(
    "--alignment",
    required=True,
    type=click.Path(exists=True),
    help="Input alignment file",
)
@click.option(
    "--output", required=True, type=click.Path(), help="Output file for anchors"
)
def get_anchors(dictionary, graph, alignment, output):
    # positioned_dict = dictionary.rstrip("pkl") + "positioned.json"
    """Process alignment and get anchors."""
    t1 = time.time()
    orchestrator = Orchestrator(dictionary, graph, alignment)
    orchestrator.process(f"{output}.anchors_info.tsv")
    print(
        f"GAF alignment processed in {time.time()-t1:.2f}", flush=True, file=sys.stderr
    )

    orchestrator.dump_anchors(output)
    orchestrator.dump_dictionary_with_counts(dictionary.rstrip("pkl") + "count.pkl")

    click.echo(f"Anchors processed and saved to {output}")

@cli.command()
@click.option(
    "--anchors",
    required=True,
    type=click.Path(exists=True),
    help="Input anchors obtained using get_anchors",
)
@click.argument(
    "fastq", 
    nargs=-1,  # Allow multiple fastq files as arguments
    type=click.Path(exists=True)
)
def verify_output(anchors, fastq):
    anchors_name = anchors.rstrip('.json').split('/')[-2]
    fastq_stripped = fastq[0].rstrip(".fastq") if fastq[0].endswith(".fastq") else fastq[0].rstrip(".fastq.gz")
    fastq_name = fastq_stripped.split('/')[-1]
    fastq_path = fastq_stripped.rstrip(fastq_name)
    out_fastq = fastq_path + f"{anchors_name}.selected.fastq"
    assembler.qc.verify_anchors_validity(anchors, fastq, out_fastq)

@cli.command()
@click.option(
    "--anchors-dict",
    required=True,
    type=click.Path(exists=True),
    help="Input anchors computed",
)
@click.option(
    "--anchors-count",
    required=True,
    type=click.Path(exists=True),
    help="Input anchors count ",
)
@click.option(
    "--out-png", required=True, help="prefix of the png files in output"
)
def plot_stats(anchors_dict, anchors_count, out_png):

    assembler.helpers.plot_count_histogram(anchors_dict, out_png + "count.png")

    assembler.helpers.plot_anchor_count_genome_distribution(
        anchors_count, out_png + "position_count.png"
    )
    



if __name__ == "__main__":
    cli()

from assembler.gaf_reader import GafReader
#from assembler.builder import AnchorDictionary
from assembler.aligner import AlignAnchor
import assembler.parser as lp
import time
from sys import stderr


class Orchestrator:

    def __init__(
        self, dictionary_path: str, graph_path: str, gaf_path: str
    ):
        """
        It initiailzes the AlignAnchor object with the packedgraph path and the dictionary generated by the assembler.builder.AnchorDictionrary object.
        It initializes the GafReader object that reads the gaf file.

        Parameters
        ----------
        sentinel_to_anchor_dictionary: dictionary
            the dctionary associating sentinels and anchors
        graph_path: string
            The filepath of the packedGraph object
        gaf_path:
            The filepath of the gaf alignment file
        """
        self.alignment_processor = AlignAnchor()
        self.alignment_processor.build(dictionary_path, graph_path)
        self.gaf_reader = GafReader(gaf_path)

    def process(self, debug_outfile):
        """
        It reads the gaf file line by line and if the line is valid, it processes it to find anchors that align to it.
        """
        times = []
        with open(debug_outfile) as debug:
            print("READ_ID\tANCHOR\tIS_MATCHING_NODES\tIS_BASELEVEL_ALIGNED")
            for line in self.gaf_reader.get_lines():
                t0 = time.time()
                parsed_data = lp.processGafLine(line)
                if parsed_data:
                    print(
                        f"PROCESSING READ {parsed_data[0]} ...",
                        end=" ",
                        flush=True,
                        file=stderr,
                    )
                    self.alignment_processor.processGafLine(parsed_data, debug)
                    t1 = time.time()
                    print(f"Done in {t1-t0}.", file=stderr)
                    times.append(t1-t0)


            # Do something with the result (e.g., print or store)
        print(f"Processed {len(times)} alignments in {sum(times):.4f}. {sum(times)/len(times):.4f} per alignment")
        print(f"Anchors-Reads path matches = {self.alignment_processor.reads_matching_anchor_path}, sequence matches = {self.alignment_processor.reads_matching_anchor_sequence}.")
        if (self.alignment_processor.reads_matching_anchor_path != 0): 
            print(f"Ratio = {(self.alignment_processor.reads_matching_anchor_sequence/self.alignment_processor.reads_matching_anchor_path):.2f}")

    def dump_anchors(self, out_file: str):
        """
        It dumps the anchors by json
        """
        self.alignment_processor.dump_valid_anchors(out_file)

    def dump_dictionary_with_counts(self, out_file: str):
        """
        It dumps the positioned anchor dictionary by json
        """
        self.alignment_processor.dump_dictionary_with_reads_counts(out_file)

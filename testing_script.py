import sys
sys.path.append('./assembler')

from assembler.handler import Orchestrator
from assembler.builder import AnchorDictionary
import time

# USED FOLDER
test_dir: str = './test/large_test/'

# INPUT FILES
graph_path: str = test_dir+'chr20.full.100k.vg'
index_path: str = test_dir+'chr20.full.100k.dist'
sample_alignment: str = test_dir+'m64012-190920-173625-Q20_chr20.full.100k.parsed.gaf'

# OUTPUT ANCHOR FILE
out_json: str = test_dir+'anchors_100k.json'

# OUTPUT DEBUG / INSPECTION FILES
anchors_file: str = test_dir+'anchors_text.txt'
out_csv_bandage: str = test_dir+'bandage_colors.csv'
out_d : str = test_dir+'anchor_sizes.csv'


# BUILD ANCHOR DICTIONARY
t0 = time.time()
dictionary_builder = AnchorDictionary()
dictionary_builder.build(graph_path, index_path)
dictionary_builder.fill_anchor_dictionary()
print(f"Anchors dictionary from {len(dictionary_builder.leaf_snarls)} snarls, containing {len(dictionary_builder.sentinel_to_anchor)} sentinels built in {time.time()-t0:.2f}", flush=True, file=sys.stderr)

# PRINT DEBUG INFO
dictionary_builder.print_anchors_from_dict(anchors_file)
dictionary_builder.print_sentinels_for_bandage(out_csv_bandage)
dictionary_builder.print_dict_sizes(out_d)

# PROCESS ALIGNMENT
t1 = time.time()
dictionary = dictionary_builder.get_dict()
orchestrator = Orchestrator(dictionary, graph_path, sample_alignment)
orchestrator.process()
print(f"GAF alignment processed in {time.time()-t1:.2f}", flush=True, file=sys.stderr)

# DUMP ANCHORS TO JSONL
orchestrator.dump_anchors(out_json)
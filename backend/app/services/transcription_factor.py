# # backend/app/services/transcription_factor.py
# import re
# import json
# import random
# import statistics
# from typing import List, Dict, Any, Optional, Tuple
# from fastapi import HTTPException
# from collections import Counter, defaultdict
# import numpy as np

# class TranscriptionFactorService:
#     """Service for transcription factor binding site analysis"""
    
#     def __init__(self):
#         # Predefined motif database (simplified JASPAR-like motifs)
#         self.motif_database = {
#             "TATA_box": {
#                 "consensus": "TATAWAWR",
#                 "pwm": self._create_pwm("TATAWAWR"),
#                 "name": "TATA-binding protein",
#                 "species": "Homo sapiens"
#             },
#             "E2F": {
#                 "consensus": "TTTCCCGC", 
#                 "pwm": self._create_pwm("TTTCCCGC"),
#                 "name": "E2F transcription factor",
#                 "species": "Homo sapiens"
#             },
#             "AP1": {
#                 "consensus": "TGASTCA",
#                 "pwm": self._create_pwm("TGASTCA"),
#                 "name": "AP-1 transcription factor",
#                 "species": "Homo sapiens"
#             },
#             "NF_kB": {
#                 "consensus": "GGGRNWYYCC",
#                 "pwm": self._create_pwm("GGGRNWYYCC"),
#                 "name": "NF-kappaB",
#                 "species": "Homo sapiens"
#             },
#             "p53": {
#                 "consensus": "RRRCWWGYYY",
#                 "pwm": self._create_pwm("RRRCWWGYYY"),
#                 "name": "p53 tumor suppressor",
#                 "species": "Homo sapiens"
#             },
#             "CREB": {
#                 "consensus": "TGACGTCA",
#                 "pwm": self._create_pwm("TGACGTCA"),
#                 "name": "cAMP response element-binding protein",
#                 "species": "Homo sapiens"
#             }
#         }
    
#     async def find_binding_sites(self, sequences: List[Dict], motif_database: str = "jaspar", parameters: Dict = None) -> Dict:
#         """Find transcription factor binding sites in sequences"""
#         try:
#             if parameters is None:
#                 parameters = {"p_value_threshold": 0.001, "motif_score_threshold": 0.8, "both_strands": True}
            
#             binding_sites = []
            
#             for seq in sequences:
#                 sequence = seq.get('sequence', '').upper()
#                 seq_sites = []
                
#                 # Search all motifs in database
#                 for motif_name, motif_data in self.motif_database.items():
#                     # Search forward strand
#                     sites = self._find_motif_sites(
#                         sequence, motif_data, motif_name, parameters, strand="+"
#                     )
#                     seq_sites.extend(sites)
                    
#                     # Search reverse strand if requested
#                     if parameters.get("both_strands", True):
#                         rev_comp = self._reverse_complement(sequence)
#                         rev_sites = self._find_motif_sites(
#                             rev_comp, motif_data, motif_name, parameters, strand="-"
#                         )
#                         # Adjust coordinates for reverse strand
#                         for site in rev_sites:
#                             site['start'] = len(sequence) - site['end'] + 1
#                             site['end'] = len(sequence) - site['start'] + len(site['sequence'])
#                         seq_sites.extend(rev_sites)
                
#                 # Sort sites by position
#                 seq_sites.sort(key=lambda x: x['start'])
                
#                 binding_sites.append({
#                     "sequence_id": seq.get('id'),
#                     "sequence_length": len(sequence),
#                     "binding_sites": seq_sites,
#                     "total_sites": len(seq_sites),
#                     "motif_density": len(seq_sites) / len(sequence) * 1000 if sequence else 0  # Sites per kb
#                 })
            
#             return {
#                 "results": binding_sites,
#                 "summary": {
#                     "total_sequences": len(sequences),
#                     "total_binding_sites": sum(len(seq['binding_sites']) for seq in binding_sites),
#                     "motifs_searched": list(self.motif_database.keys()),
#                     "average_sites_per_sequence": sum(len(seq['binding_sites']) for seq in binding_sites) / len(binding_sites) if binding_sites else 0
#                 },
#                 "parameters": parameters,
#                 "database": motif_database
#             }
#         except Exception as e:
#             raise HTTPException(status_code=400, detail=f"Error finding binding sites: {str(e)}")

#     async def predict_tfbs(self, sequences: List[Dict], custom_motifs: List[Dict] = None, parameters: Dict = None) -> Dict:
#         """Predict transcription factor binding sites using custom motifs"""
#         try:
#             if parameters is None:
#                 parameters = {"score_threshold": 0.85, "background_gc": 0.4}
            
#             # Use custom motifs if provided, otherwise use default database
#             motifs_to_search = {}
            
#             if custom_motifs:
#                 for motif in custom_motifs:
#                     motifs_to_search[motif['name']] = {
#                         "consensus": motif.get('consensus', ''),
#                         "pwm": motif.get('pwm', self._create_pwm(motif.get('consensus', ''))),
#                         "name": motif['name'],
#                         "threshold": motif.get('threshold', parameters['score_threshold'])
#                     }
#             else:
#                 motifs_to_search = self.motif_database
            
#             predictions = []
            
#             for seq in sequences:
#                 sequence = seq.get('sequence', '').upper()
#                 predicted_sites = []
                
#                 for motif_name, motif_data in motifs_to_search.items():
#                     # Use PWM scoring
#                     sites = self._pwm_scan(sequence, motif_data, parameters)
#                     predicted_sites.extend(sites)
                
#                 # Filter by score threshold
#                 filtered_sites = [
#                     site for site in predicted_sites 
#                     if site['score'] >= parameters.get('score_threshold', 0.85)
#                 ]
                
#                 predictions.append({
#                     "sequence_id": seq.get('id'),
#                     "predicted_sites": filtered_sites,
#                     "total_predictions": len(filtered_sites),
#                     "high_confidence_sites": len([s for s in filtered_sites if s['score'] >= 0.9])
#                 })
            
#             return {
#                 "predictions": predictions,
#                 "summary": {
#                     "total_sequences": len(sequences),
#                     "total_predictions": sum(len(p['predicted_sites']) for p in predictions),
#                     "motifs_used": list(motifs_to_search.keys())
#                 },
#                 "parameters": parameters
#             }
#         except Exception as e:
#             raise HTTPException(status_code=400, detail=f"Error predicting TFBS: {str(e)}")

#     async def scan_motif_database(self, sequences: List[Dict], database_name: str = "jaspar", parameters: Dict = None) -> Dict:
#         """Scan sequences against motif database"""
#         try:
#             if parameters is None:
#                 parameters = {"matrix_threshold": 0.8, "core_threshold": 0.9}
            
#             # Simulate scanning against different databases
#             available_databases = {
#                 "jaspar": self.motif_database,
#                 "transfac": self._get_transfac_motifs(),
#                 "homer": self._get_homer_motifs(),
#                 "cisbp": self._get_cisbp_motifs()
#             }
            
#             if database_name not in available_databases:
#                 raise ValueError(f"Database {database_name} not available")
            
#             motifs = available_databases[database_name]
#             scan_results = []
            
#             for seq in sequences:
#                 sequence = seq.get('sequence', '').upper()
#                 sequence_results = {
#                     "sequence_id": seq.get('id'),
#                     "database_hits": [],
#                     "motif_matches": {}
#                 }
                
#                 for motif_name, motif_data in motifs.items():
#                     hits = self._scan_sequence_with_motif(sequence, motif_data, parameters)
#                     if hits:
#                         sequence_results["database_hits"].extend(hits)
#                         sequence_results["motif_matches"][motif_name] = len(hits)
                
#                 scan_results.append(sequence_results)
            
#             return {
#                 "scan_results": scan_results,
#                 "database_info": {
#                     "name": database_name,
#                     "motif_count": len(motifs),
#                     "version": "1.0"  # Mock version
#                 },
#                 "parameters": parameters,
#                 "summary": {
#                     "total_sequences_scanned": len(sequences),
#                     "total_hits": sum(len(r['database_hits']) for r in scan_results)
#                 }
#             }
#         except Exception as e:
#             raise HTTPException(status_code=400, detail=f"Error scanning motif database: {str(e)}")

#     async def utility_function(self, data: Any, operation: str, parameters: Dict = None) -> Any:
#         """General utility function for various operations"""
#         try:
#             if operation == "validate_sequences":
#                 return self._validate_sequences(data)
#             elif operation == "reverse_complement":
#                 return self._reverse_complement_sequences(data)
#             elif operation == "translate_dna":
#                 return self._translate_dna(data, parameters)
#             elif operation == "calculate_molecular_weight":
#                 return self._calculate_molecular_weight(data)
#             elif operation == "find_orfs":
#                 return self._find_open_reading_frames(data, parameters)
#             elif operation == "gc_skew":
#                 return self._calculate_gc_skew(data, parameters)
#             elif operation == "codon_usage":
#                 return self._analyze_codon_usage(data)
#             elif operation == "restriction_sites":
#                 return self._find_restriction_sites(data, parameters)
#             else:
#                 raise ValueError(f"Utility operation {operation} not supported")
#         except Exception as e:
#             raise HTTPException(status_code=400, detail=f"Error in utility function: {str(e)}")

#     # Helper methods
#     def _find_motif_sites(self, sequence: str, motif_data: Dict, motif_name: str, parameters: Dict, strand: str = "+") -> List[Dict]:
#         """Find individual motif sites in sequence"""
#         sites = []
#         consensus = motif_data.get('consensus', '')
        
#         if not consensus:
#             return sites
        
#         # Convert IUPAC codes to regex pattern
#         regex_pattern = self._iupac_to_regex(consensus)
        
#         # Find all matches
#         for match in re.finditer(regex_pattern, sequence):
#             # Calculate PWM score if available
#             score = self._calculate_pwm_score(match.group(), motif_data.get('pwm', {}))
            
#             if score >= parameters.get('motif_score_threshold', 0.8):
#                 sites.append({
#                     "motif_name": motif_name,
#                     "start": match.start() + 1,  # 1-based coordinates
#                     "end": match.end(),
#                     "strand": strand,
#                     "sequence": match.group(),
#                     "score": score,
#                     "p_value": self._calculate_p_value(score, len(match.group()))
#                 })
        
#         return sites

#     def _pwm_scan(self, sequence: str, motif_data: Dict, parameters: Dict) -> List[Dict]:
#         """Scan sequence using Position Weight Matrix"""
#         sites = []
#         pwm = motif_data.get('pwm', {})
#         motif_length = len(motif_data.get('consensus', ''))
        
#         if not pwm or motif_length == 0:
#             return sites
        
#         for i in range(len(sequence) - motif_length + 1):
#             subsequence = sequence[i:i + motif_length]
#             score = self._calculate_pwm_score(subsequence, pwm)
            
#             if score >= parameters.get('score_threshold', 0.85):
#                 sites.append({
#                     "motif_name": motif_data.get('name', 'unknown'),
#                     "start": i + 1,
#                     "end": i + motif_length,
#                     "strand": "+",
#                     "sequence": subsequence,
#                     "score": score,
#                     "p_value": self._calculate_p_value(score, motif_length)
#                 })
        
#         return sites

#     def _scan_sequence_with_motif(self, sequence: str, motif_data: Dict, parameters: Dict) -> List[Dict]:
#         """Scan sequence with specific motif"""
#         consensus = motif_data.get('consensus', '')
#         if not consensus:
#             return []
        
#         return self._find_motif_sites(sequence, motif_data, motif_data.get('name', 'unknown'), parameters)

#     def _create_pwm(self, consensus: str) -> Dict[str, List[float]]:
#         """Create Position Weight Matrix from consensus sequence"""
#         pwm = {'A': [], 'C': [], 'G': [], 'T': []}
        
#         for pos, base in enumerate(consensus.upper()):
#             if base in 'ATCG':
#                 # High probability for consensus base
#                 for nucleotide in 'ATCG':
#                     if nucleotide == base:
#                         pwm[nucleotide].append(0.8)
#                     else:
#                         pwm[nucleotide].append(0.067)  # (1-0.8)/3
#             else:
#                 # Handle IUPAC codes
#                 allowed_bases = self._iupac_to_bases(base)
#                 prob_per_base = 0.8 / len(allowed_bases)
#                 background_prob = 0.2 / (4 - len(allowed_bases)) if len(allowed_bases) < 4 else 0
                
#                 for nucleotide in 'ATCG':
#                     if nucleotide in allowed_bases:
#                         pwm[nucleotide].append(prob_per_base)
#                     else:
#                         pwm[nucleotide].append(background_prob)
        
#         return pwm

#     def _calculate_pwm_score(self, sequence: str, pwm: Dict[str, List[float]]) -> float:
#         """Calculate PWM score for a sequence"""
#         if not pwm or not sequence:
#             return 0.0
        
#         score = 1.0
#         for i, base in enumerate(sequence.upper()):
#             if base in pwm and i < len(pwm[base]):
#                 score *= pwm[base][i]
#             else:
#                 score *= 0.25  # Background probability
        
#         # Convert to log-odds score and normalize
#         import math
#         log_score = math.log(score) if score > 0 else -100
#         return max(0, (log_score + 20) / 20)  # Normalize to 0-1

#     def _calculate_p_value(self, score: float, motif_length: int) -> float:
#         """Calculate approximate p-value for motif score"""
#         # Simplified p-value calculation
#         # In reality, this would use proper statistical models
#         return max(0.0001, (1 - score) * random.uniform(0.001, 0.1))

#     def _iupac_to_regex(self, iupac_sequence: str) -> str:
#         """Convert IUPAC sequence to regex pattern"""
#         iupac_codes = {
#             'W': '[AT]', 'S': '[GC]', 'M': '[AC]', 'K': '[GT]',
#             'R': '[AG]', 'Y': '[CT]', 'B': '[GTC]', 'D': '[GAT]',
#             'H': '[ACT]', 'V': '[GCA]', 'N': '[ATCG]'
#         }
        
#         regex_pattern = iupac_sequence.upper()
#         for code, replacement in iupac_codes.items():
#             regex_pattern = regex_pattern.replace(code, replacement)
        
#         return regex_pattern

#     def _iupac_to_bases(self, iupac_code: str) -> List[str]:
#         """Convert IUPAC code to list of bases"""
#         iupac_map = {
#             'W': ['A', 'T'], 'S': ['G', 'C'], 'M': ['A', 'C'], 'K': ['G', 'T'],
#             'R': ['A', 'G'], 'Y': ['C', 'T'], 'B': ['G', 'T', 'C'], 'D': ['G', 'A', 'T'],
#             'H': ['A', 'C', 'T'], 'V': ['G', 'C', 'A'], 'N': ['A', 'T', 'C', 'G']
#         }
#         return iupac_map.get(iupac_code.upper(), [iupac_code.upper()])

#     def _reverse_complement(self, sequence: str) -> str:
#         """Calculate reverse complement of DNA sequence"""
#         complement = {'A': 'T', 'T': 'A', 'C': 'G', 'G': 'C', 'N': 'N'}
#         return ''.join(complement.get(base.upper(), base) for base in reversed(sequence))

#     # Utility functions
#     def _validate_sequences(self, sequences: List[Dict]) -> Dict:
#         """Validate sequence data"""
#         valid_sequences = []
#         invalid_sequences = []
        
#         for seq in sequences:
#             sequence = seq.get('sequence', '').upper()
#             valid_chars = set('ATCGRYSWKMBDHVN')  # DNA with IUPAC codes
            
#             is_valid = True
#             errors = []
            
#             if not sequence:
#                 is_valid = False
#                 errors.append("Empty sequence")
#             elif not set(sequence).issubset(valid_chars):
#                 is_valid = False
#                 invalid_chars = set(sequence) - valid_chars
#                 errors.append(f"Invalid characters: {', '.join(invalid_chars)}")
            
#             if is_valid:
#                 valid_sequences.append(seq)
#             else:
#                 invalid_sequences.append({
#                     **seq,
#                     "validation_errors": errors
#                 })
        
#         return {
#             "valid_sequences": valid_sequences,
#             "invalid_sequences": invalid_sequences,
#             "validation_summary": {
#                 "total": len(sequences),
#                 "valid": len(valid_sequences),
#                 "invalid": len(invalid_sequences),
#                 "validation_rate": len(valid_sequences) / len(sequences) * 100 if sequences else 0
#             }
#         }

#     def _reverse_complement_sequences(self, sequences: List[Dict]) -> List[Dict]:
#         """Calculate reverse complement for multiple sequences"""
#         result = []
        
#         for seq in sequences:
#             sequence_data = seq.get('sequence', '')
            
#             if seq.get('sequence_type', 'DNA') not in ['DNA', 'RNA']:
#                 continue  # Skip non-nucleotide sequences
            
#             reverse_comp = self._reverse_complement(sequence_data)
            
#             result_seq = seq.copy()
#             result_seq['sequence'] = reverse_comp
#             result_seq['id'] = f"{seq.get('id', '')}_rc"
#             result_seq['description'] = f"Reverse complement of {seq.get('description', seq.get('id', ''))}"
            
#             result.append(result_seq)
        
#         return result

#     def _translate_dna(self, sequences: List[Dict], parameters: Dict = None) -> List[Dict]:
#         """Translate DNA sequences to protein"""
#         if parameters is None:
#             parameters = {"genetic_code": 1, "reading_frame": 1}
        
#         result = []
        
#         # Standard genetic code
#         codon_table = {
#             'TTT': 'F', 'TTC': 'F', 'TTA': 'L', 'TTG': 'L',
#             'TCT': 'S', 'TCC': 'S', 'TCA': 'S', 'TCG': 'S',
#             'TAT': 'Y', 'TAC': 'Y', 'TAA': '*', 'TAG': '*',
#             'TGT': 'C', 'TGC': 'C', 'TGA': '*', 'TGG': 'W',
#             'CTT': 'L', 'CTC': 'L', 'CTA': 'L', 'CTG': 'L',
#             'CCT': 'P', 'CCC': 'P', 'CCA': 'P', 'CCG': 'P',
#             'CAT': 'H', 'CAC': 'H', 'CAA': 'Q', 'CAG': 'Q',
#             'CGT': 'R', 'CGC': 'R', 'CGA': 'R', 'CGG': 'R',
#             'ATT': 'I', 'ATC': 'I', 'ATA': 'I', 'ATG': 'M',
#             'ACT': 'T', 'ACC': 'T', 'ACA': 'T', 'ACG': 'T',
#             'AAT': 'N', 'AAC': 'N', 'AAA': 'K', 'AAG': 'K',
#             'AGT': 'S', 'AGC': 'S', 'AGA': 'R', 'AGG': 'R',
#             'GTT': 'V', 'GTC': 'V', 'GTA': 'V', 'GTG': 'V',
#             'GCT': 'A', 'GCC': 'A', 'GCA': 'A', 'GCG': 'A',
#             'GAT': 'D', 'GAC': 'D', 'GAA': 'E', 'GAG': 'E',
#             'GGT': 'G', 'GGC': 'G', 'GGA': 'G', 'GGG': 'G'
#         }
        
#         for seq in sequences:
#             sequence_data = seq.get('sequence', '').upper()
#             reading_frame = parameters.get('reading_frame', 1)
            
#             # Adjust for reading frame (1, 2, or 3)
#             start_pos = reading_frame - 1
#             protein_sequence = ""
            
#             # Translate in codons
#             for i in range(start_pos, len(sequence_data) - 2, 3):
#                 codon = sequence_data[i:i+3]
#                 if len(codon) == 3:
#                     amino_acid = codon_table.get(codon, 'X')  # X for unknown
#                     protein_sequence += amino_acid
            
#             translated_seq = seq.copy()
#             translated_seq['sequence'] = protein_sequence
#             translated_seq['sequence_type'] = 'PROTEIN'
#             translated_seq['id'] = f"{seq.get('id', '')}_translated_frame{reading_frame}"
#             translated_seq['description'] = f"Translation of {seq.get('id', '')} (frame {reading_frame})"
#             translated_seq['reading_frame'] = reading_frame
            
#             result.append(translated_seq)
        
#         return result

#     def _calculate_molecular_weight(self, sequences: List[Dict]) -> List[Dict]:
#         """Calculate molecular weight of sequences"""
#         # Molecular weights (Da) for amino acids
#         aa_weights = {
#             'A': 89.1, 'R': 174.2, 'N': 132.1, 'D': 133.1, 'C': 121.2,
#             'Q': 146.1, 'E': 147.1, 'G': 75.1, 'H': 155.2, 'I': 131.2,
#             'L': 131.2, 'K': 146.2, 'M': 149.2, 'F': 165.2, 'P': 115.1,
#             'S': 105.1, 'T': 119.1, 'W': 204.2, 'Y': 181.2, 'V': 117.1
#         }
        
#         # Nucleotide weights (Da)
#         nucleotide_weights = {'A': 331.2, 'T': 322.2, 'C': 307.2, 'G': 347.2, 'U': 308.2}
        
#         result = []
        
#         for seq in sequences:
#             sequence_data = seq.get('sequence', '').upper()
#             sequence_type = seq.get('sequence_type', 'DNA')
            
#             molecular_weight = 0.0
            
#             if sequence_type == 'PROTEIN':
#                 for aa in sequence_data:
#                     molecular_weight += aa_weights.get(aa, 0)
#                 # Subtract water molecules for peptide bonds
#                 molecular_weight -= (len(sequence_data) - 1) * 18.02 if len(sequence_data) > 1 else 0
#             else:  # DNA or RNA
#                 for nucleotide in sequence_data:
#                     molecular_weight += nucleotide_weights.get(nucleotide, 0)
            
#             result_seq = seq.copy()
#             result_seq['molecular_weight'] = round(molecular_weight, 2)
#             result_seq['molecular_weight_kda'] = round(molecular_weight / 1000, 2)
            
#             result.append(result_seq)
        
#         return result

#     def _find_open_reading_frames(self, sequences: List[Dict], parameters: Dict = None) -> List[Dict]:
#         """Find open reading frames in DNA sequences"""
#         if parameters is None:
#             parameters = {"min_orf_length": 100, "start_codons": ["ATG"], "stop_codons": ["TAA", "TAG", "TGA"]}
        
#         result = []
        
#         for seq in sequences:
#             sequence_data = seq.get('sequence', '').upper()
#             orfs = []
            
#             start_codons = parameters.get('start_codons', ['ATG'])
#             stop_codons = parameters.get('stop_codons', ['TAA', 'TAG', 'TGA'])
#             min_length = parameters.get('min_orf_length', 100)
            
#             # Search in all three reading frames on both strands
#             for strand in ['+', '-']:
#                 search_seq = sequence_data if strand == '+' else self._reverse_complement(sequence_data)
                
#                 for frame in range(3):
#                     frame_orfs = self._find_orfs_in_frame(search_seq, frame, start_codons, stop_codons, min_length)
                    
#                     # Adjust coordinates for strand and frame
#                     for orf in frame_orfs:
#                         if strand == '-':
#                             # Convert coordinates back to forward strand
#                             original_start = len(sequence_data) - orf['end'] + 1
#                             original_end = len(sequence_data) - orf['start'] + 1
#                             orf['start'] = original_start
#                             orf['end'] = original_end
                        
#                         orf['strand'] = strand
#                         orf['reading_frame'] = frame + 1
                    
#                     orfs.extend(frame_orfs)
            
#             # Sort ORFs by length (descending)
#             orfs.sort(key=lambda x: x['length'], reverse=True)
            
#             result_seq = seq.copy()
#             result_seq['orfs'] = orfs
#             result_seq['total_orfs'] = len(orfs)
#             result_seq['longest_orf'] = orfs[0]['length'] if orfs else 0
            
#             result.append(result_seq)
        
#         return result

#     def _find_orfs_in_frame(self, sequence: str, frame: int, start_codons: List[str], stop_codons: List[str], min_length: int) -> List[Dict]:
#         """Find ORFs in a specific reading frame"""
#         orfs = []
#         in_orf = False
#         orf_start = 0
        
#         for i in range(frame, len(sequence) - 2, 3):
#             codon = sequence[i:i+3]
            
#             if len(codon) != 3:
#                 break
            
#             if not in_orf and codon in start_codons:
#                 # Start of ORF
#                 in_orf = True
#                 orf_start = i
#             elif in_orf and codon in stop_codons:
#                 # End of ORF
#                 orf_length = i + 3 - orf_start
#                 if orf_length >= min_length:
#                     orfs.append({
#                         'start': orf_start + 1,  # 1-based
#                         'end': i + 3,
#                         'length': orf_length,
#                         'sequence': sequence[orf_start:i+3],
#                         'start_codon': sequence[orf_start:orf_start+3],
#                         'stop_codon': codon
#                     })
#                 in_orf = False
        
#         return orfs

#     def _calculate_gc_skew(self, sequences: List[Dict], parameters: Dict = None) -> List[Dict]:
#         """Calculate GC skew for sequences"""
#         if parameters is None:
#             parameters = {"window_size": 1000, "step_size": 100}
        
#         result = []
        
#         for seq in sequences:
#             sequence_data = seq.get('sequence', '').upper()
#             window_size = parameters.get('window_size', 1000)
#             step_size = parameters.get('step_size', 100)
            
#             gc_skew_values = []
#             positions = []
            
#             for i in range(0, len(sequence_data) - window_size + 1, step_size):
#                 window = sequence_data[i:i + window_size]
#                 g_count = window.count('G')
#                 c_count = window.count('C')
                
#                 if g_count + c_count > 0:
#                     gc_skew = (g_count - c_count) / (g_count + c_count)
#                 else:
#                     gc_skew = 0.0
                
#                 gc_skew_values.append(gc_skew)
#                 positions.append(i + window_size // 2)  # Center of window
            
#             result_seq = seq.copy()
#             result_seq['gc_skew'] = {
#                 'values': gc_skew_values,
#                 'positions': positions,
#                 'window_size': window_size,
#                 'step_size': step_size,
#                 'mean_skew': statistics.mean(gc_skew_values) if gc_skew_values else 0,
#                 'max_skew': max(gc_skew_values) if gc_skew_values else 0,
#                 'min_skew': min(gc_skew_values) if gc_skew_values else 0
#             }
            
#             result.append(result_seq)
        
#         return result

#     def _analyze_codon_usage(self, sequences: List[Dict]) -> List[Dict]:
#         """Analyze codon usage patterns"""
#         result = []
        
#         for seq in sequences:
#             sequence_data = seq.get('sequence', '').upper()
            
#             if seq.get('sequence_type', 'DNA') != 'DNA':
#                 continue  # Skip non-DNA sequences
            
#             codon_counts = Counter()
#             total_codons = 0
            
#             # Count codons in all reading frames
#             for frame in range(3):
#                 for i in range(frame, len(sequence_data) - 2, 3):
#                     codon = sequence_data[i:i+3]
#                     if len(codon) == 3 and all(c in 'ATCG' for c in codon):
#                         codon_counts[codon] += 1
#                         total_codons += 1
            
#             # Calculate frequencies
#             codon_frequencies = {}
#             for codon, count in codon_counts.items():
#                 codon_frequencies[codon] = count / total_codons if total_codons > 0 else 0
            
#             # Group by amino acid
#             aa_codon_usage = defaultdict(list)
#             codon_table = {
#                 'TTT': 'F', 'TTC': 'F', 'TTA': 'L', 'TTG': 'L',
#                 'TCT': 'S', 'TCC': 'S', 'TCA': 'S', 'TCG': 'S',
#                 # ... (would include full codon table)
#             }
            
#             for codon, freq in codon_frequencies.items():
#                 aa = codon_table.get(codon, 'X')
#                 aa_codon_usage[aa].append({'codon': codon, 'frequency': freq})
            
#             result_seq = seq.copy()
#             result_seq['codon_usage'] = {
#                 'codon_counts': dict(codon_counts),
#                 'codon_frequencies': codon_frequencies,
#                 'aa_codon_usage': dict(aa_codon_usage),
#                 'total_codons': total_codons,
#                 'unique_codons': len(codon_counts)
#             }
            
#             result.append(result_seq)
        
#         return result

#     def _find_restriction_sites(self, sequences: List[Dict], parameters: Dict = None) -> List[Dict]:
#         """Find restriction enzyme cut sites"""
#         if parameters is None:
#             parameters = {"enzymes": ["EcoRI", "BamHI", "HindIII"]}
        
#         # Common restriction enzymes
#         enzyme_sites = {
#             "EcoRI": "GAATTC",
#             "BamHI": "GGATCC", 
#             "HindIII": "AAGCTT",
#             "XhoI": "CTCGAG",
#             "SacI": "GAGCTC",
#             "KpnI": "GGTACC",
#             "SmaI": "CCCGGG",
#             "PstI": "CTGCAG",
#             "XbaI": "TCTAGA",
#             "SpeI": "ACTAGT"
#         }
        
#         result = []
        
#         for seq in sequences:
#             sequence_data = seq.get('sequence', '').upper()
#             all_sites = []
            
#             for enzyme in parameters.get('enzymes', ['EcoRI']):
#                 if enzyme in enzyme_sites:
#                     recognition_seq = enzyme_sites[enzyme]
                    
#                     # Find all occurrences
#                     start = 0
#                     while True:
#                         pos = sequence_data.find(recognition_seq, start)
#                         if pos == -1:
#                             break
                        
#                         all_sites.append({
#                             'enzyme': enzyme,
#                             'recognition_sequence': recognition_seq,
#                             'position': pos + 1,  # 1-based
#                             'cut_position': pos + len(recognition_seq) // 2,  # Approximate
#                             'strand': '+'
#                         })
                        
#                         start = pos + 1
            
#             # Sort by position
#             all_sites.sort(key=lambda x: x['position'])
            
#             result_seq = seq.copy()
#             result_seq['restriction_sites'] = all_sites
#             result_seq['total_sites'] = len(all_sites)
#             result_seq['enzymes_found'] = list(set(site['enzyme'] for site in all_sites))
            
#             result.append(result_seq)
        
#         return result

#     # Database simulation methods
#     def _get_transfac_motifs(self) -> Dict:
#         """Get TRANSFAC-like motifs (simplified)"""
#         return {
#             "SP1": {
#                 "consensus": "GGGCGG",
#                 "pwm": self._create_pwm("GGGCGG"),
#                 "name": "SP1 transcription factor"
#             },
#             "STAT1": {
#                 "consensus": "TTCYNRGAA",
#                 "pwm": self._create_pwm("TTCYNRGAA"),
#                 "name": "STAT1 transcription factor"
#             }
#         }

#     def _get_homer_motifs(self) -> Dict:
#         """Get HOMER-like motifs (simplified)"""
#         return {
#             "OCT4": {
#                 "consensus": "ATGCAAAT",
#                 "pwm": self._create_pwm("ATGCAAAT"),
#                 "name": "OCT4 transcription factor"
#             },
#             "NANOG": {
#                 "consensus": "TTATGC",
#                 "pwm": self._create_pwm("TTATGC"),
#                 "name": "NANOG transcription factor"
#             }
#         }

#     def _get_cisbp_motifs(self) -> Dict:
#         """Get CIS-BP-like motifs (simplified)"""
#         return {
#             "FOXO1": {
#                 "consensus": "RYMAAYA",
#                 "pwm": self._create_pwm("RYMAAYA"),
#                 "name": "FOXO1 transcription factor"
#             },
#             "HNF4A": {
#                 "consensus": "RGGNCAAAGGTCA",
#                 "pwm": self._create_pwm("RGGNCAAAGGTCA"),
#                 "name": "HNF4A transcription factor"
#             }
#         }

# backend/app/services/transcription_factor.py
import asyncio
import numpy as np
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict
import logging
import math

logger = logging.getLogger(__name__)

@dataclass
class MotifMatch:
    """Data class for motif match results"""
    sequence_id: str
    motif_id: str
    start_position: int
    end_position: int
    strand: str
    score: float
    sequence_match: str
    p_value: Optional[float] = None

@dataclass
class PositionWeightMatrix:
    """Position Weight Matrix for transcription factor binding sites"""
    motif_id: str
    matrix: List[List[float]]  # 4 x length matrix (A, C, G, T)
    length: int
    consensus: str
    information_content: List[float]

class TranscriptionFactorService:
    """Service for transcription factor binding site analysis"""
    
    def __init__(self):
        self.nucleotides = ['A', 'C', 'G', 'T']
        self.complement = {'A': 'T', 'T': 'A', 'C': 'G', 'G': 'C'}
        
        # Built-in motif database (simplified JASPAR-like entries)
        self.builtin_motifs = self._initialize_builtin_motifs()
    
    def _initialize_builtin_motifs(self) -> Dict[str, PositionWeightMatrix]:
        """Initialize built-in motif database"""
        motifs = {}
        
        # p53 binding site motif (simplified)
        p53_matrix = [
            [0.1, 0.8, 0.05, 0.05],  # Position 1: prefer G
            [0.05, 0.05, 0.85, 0.05], # Position 2: prefer G
            [0.05, 0.8, 0.1, 0.05],   # Position 3: prefer C
            [0.8, 0.05, 0.1, 0.05],   # Position 4: prefer A
            [0.05, 0.05, 0.05, 0.85], # Position 5: prefer T
            [0.8, 0.05, 0.1, 0.05],   # Position 6: prefer A
            [0.05, 0.8, 0.1, 0.05],   # Position 7: prefer C
            [0.05, 0.05, 0.85, 0.05], # Position 8: prefer G
            [0.8, 0.05, 0.1, 0.05],   # Position 9: prefer A
            [0.05, 0.05, 0.05, 0.85]  # Position 10: prefer T
        ]
        
        motifs['TP53_01'] = PositionWeightMatrix(
            motif_id='TP53_01',
            matrix=p53_matrix,
            length=10,
            consensus='GGCATACGAT',
            information_content=self._calculate_information_content(p53_matrix)
        )
        
        # NF-kB binding site motif
        nfkb_matrix = [
            [0.1, 0.1, 0.75, 0.05],   # G
            [0.05, 0.05, 0.85, 0.05], # G
            [0.05, 0.05, 0.85, 0.05], # G
            [0.7, 0.1, 0.1, 0.1],     # A
            [0.8, 0.05, 0.1, 0.05],   # A
            [0.05, 0.05, 0.05, 0.85], # T
            [0.05, 0.8, 0.1, 0.05],   # C
            [0.05, 0.8, 0.1, 0.05],   # C
        ]
        
        motifs['NFKB_01'] = PositionWeightMatrix(
            motif_id='NFKB_01',
            matrix=nfkb_matrix,
            length=8,
            consensus='GGGAATCC',
            information_content=self._calculate_information_content(nfkb_matrix)
        )
        
        # TATA box motif
        tata_matrix = [
            [0.05, 0.05, 0.05, 0.85], # T
            [0.85, 0.05, 0.05, 0.05], # A
            [0.05, 0.05, 0.05, 0.85], # T
            [0.85, 0.05, 0.05, 0.05], # A
            [0.25, 0.25, 0.25, 0.25], # N (any)
            [0.85, 0.05, 0.05, 0.05], # A
            [0.05, 0.05, 0.05, 0.85], # T
            [0.05, 0.05, 0.8, 0.1],   # G
        ]
        
        motifs['TATA_01'] = PositionWeightMatrix(
            motif_id='TATA_01',
            matrix=tata_matrix,
            length=8,
            consensus='TATANATG',
            information_content=self._calculate_information_content(tata_matrix)
        )
        
        return motifs
    
    def _calculate_information_content(self, matrix: List[List[float]]) -> List[float]:
        """Calculate information content for each position in PWM"""
        information_content = []
        
        for position in matrix:
            ic = 0
            for prob in position:
                if prob > 0:
                    ic += prob * math.log2(prob * 4)  # 4 for 4 nucleotides
            information_content.append(ic)
        
        return information_content
    
    async def find_binding_sites(
        self, 
        sequences: List[Dict], 
        motif_database: str = "builtin", 
        parameters: Dict = None
    ) -> Dict:
        """Find transcription factor binding sites in sequences"""
        if not sequences:
            return {"error": "No sequences provided"}
        
        if parameters is None:
            parameters = {}
        
        # Default parameters
        threshold = parameters.get('threshold', 0.8)
        scan_both_strands = parameters.get('scan_both_strands', True)
        motif_ids = parameters.get('motif_ids', None)  # None means scan all motifs
        
        try:
            # Get motifs from specified database
            motifs = await self._get_motifs_from_database(motif_database, motif_ids)
            
            if not motifs:
                return {"error": f"No motifs found in database: {motif_database}"}
            
            # Scan all sequences for all motifs
            all_matches = []
            sequence_results = {}
            
            for seq in sequences:
                seq_id = seq.get('id', seq.get('name', 'unknown'))
                sequence_str = seq.get('sequence', '').upper()
                
                if not sequence_str:
                    continue
                
                seq_matches = []
                
                for motif in motifs.values():
                    # Scan forward strand
                    matches = await self._scan_sequence_for_motif(
                        sequence_str, motif, threshold, '+', seq_id
                    )
                    seq_matches.extend(matches)
                    
                    # Scan reverse strand if requested
                    if scan_both_strands:
                        reverse_seq = self._reverse_complement(sequence_str)
                        reverse_matches = await self._scan_sequence_for_motif(
                            reverse_seq, motif, threshold, '-', seq_id
                        )
                        seq_matches.extend(reverse_matches)
                
                sequence_results[seq_id] = seq_matches
                all_matches.extend(seq_matches)
            
            # Compile summary statistics
            summary = self._compile_binding_site_summary(all_matches, motifs)
            
            return {
                "status": "success",
                "parameters_used": {
                    "threshold": threshold,
                    "scan_both_strands": scan_both_strands,
                    "motif_database": motif_database
                },
                "total_matches": len(all_matches),
                "sequence_results": sequence_results,
                "summary": summary,
                "motifs_scanned": list(motifs.keys())
            }
            
        except Exception as e:
            logger.error(f"Error finding binding sites: {str(e)}")
            return {"error": f"Failed to find binding sites: {str(e)}"}
    
    async def scan_motifs(
        self, 
        sequences: List[Dict], 
        motif_matrices: List[Dict], 
        parameters: Dict = None
    ) -> Dict:
        """Scan sequences for custom motif matrices"""
        if not sequences or not motif_matrices:
            return {"error": "Sequences and motif matrices are required"}
        
        if parameters is None:
            parameters = {}
        
        threshold = parameters.get('threshold', 0.8)
        
        try:
            # Convert motif matrices to PWM objects
            pwms = {}
            for motif_data in motif_matrices:
                pwm = self._create_pwm_from_matrix(motif_data)
                pwms[pwm.motif_id] = pwm
            
            # Use the existing find_binding_sites method with custom motifs
            custom_db = "custom"
            self._temp_motifs = pwms  # Temporary storage for custom motifs
            
            results = await self.find_binding_sites(sequences, custom_db, parameters)
            
            # Clean up temporary storage
            if hasattr(self, '_temp_motifs'):
                delattr(self, '_temp_motifs')
            
            return results
            
        except Exception as e:
            logger.error(f"Error scanning custom motifs: {str(e)}")
            return {"error": f"Failed to scan motifs: {str(e)}"}
    
    async def _get_motifs_from_database(self, database: str, motif_ids: Optional[List[str]] = None) -> Dict[str, PositionWeightMatrix]:
        """Get motifs from specified database"""
        if database == "builtin":
            motifs = self.builtin_motifs.copy()
        elif database == "custom" and hasattr(self, '_temp_motifs'):
            motifs = self._temp_motifs.copy()
        else:
            # In a real implementation, this would connect to JASPAR, HOCOMOCO, etc.
            logger.warning(f"Database {database} not implemented, using builtin")
            motifs = self.builtin_motifs.copy()
        
        # Filter by motif IDs if specified
        if motif_ids:
            motifs = {k: v for k, v in motifs.items() if k in motif_ids}
        
        return motifs
    
    async def _scan_sequence_for_motif(
        self, 
        sequence: str, 
        motif: PositionWeightMatrix, 
        threshold: float, 
        strand: str, 
        seq_id: str
    ) -> List[MotifMatch]:
        """Scan a single sequence for a specific motif"""
        matches = []
        seq_length = len(sequence)
        motif_length = motif.length
        
        # Slide motif across sequence
        for start_pos in range(seq_length - motif_length + 1):
            subseq = sequence[start_pos:start_pos + motif_length]
            
            # Calculate PWM score
            score = self._calculate_pwm_score(subseq, motif)
            
            if score >= threshold:
                match = MotifMatch(
                    sequence_id=seq_id,
                    motif_id=motif.motif_id,
                    start_position=start_pos + 1,  # 1-based indexing
                    end_position=start_pos + motif_length,
                    strand=strand,
                    score=score,
                    sequence_match=subseq,
                    p_value=self._calculate_p_value(score, motif)
                )
                matches.append(match)
        
        return matches
    
    def _calculate_pwm_score(self, sequence: str, motif: PositionWeightMatrix) -> float:
        """Calculate PWM score for a sequence"""
        if len(sequence) != motif.length:
            return 0.0
        
        score = 1.0
        
        for i, nucleotide in enumerate(sequence):
            if nucleotide not in self.nucleotides:
                return 0.0  # Invalid nucleotide
            
            nuc_index = self.nucleotides.index(nucleotide)
            prob = motif.matrix[i][nuc_index]
            
            if prob <= 0:
                return 0.0
            
            score *= prob
        
        # Convert to log-odds score
        max_score = 1.0
        for position in motif.matrix:
            max_score *= max(position)
        
        return score / max_score if max_score > 0 else 0.0
    
    def _calculate_p_value(self, score: float, motif: PositionWeightMatrix) -> float:
        """Calculate approximate p-value for motif match"""
        # Simplified p-value calculation
        # In practice, this would use more sophisticated statistical models
        
        # Convert score to z-score approximation
        # This is a simplified approach - real implementations use more complex methods
        z_score = (score - 0.25) / 0.2  # Rough approximation
        
        # Convert to p-value (very approximate)
        if z_score > 0:
            p_value = 1.0 / (1.0 + math.exp(z_score * 2))
        else:
            p_value = 0.5
        
        return min(p_value, 1.0)
    
    def _reverse_complement(self, sequence: str) -> str:
        """Generate reverse complement of DNA sequence"""
        return ''.join(self.complement.get(base, base) for base in reversed(sequence))
    
    def _create_pwm_from_matrix(self, motif_data: Dict) -> PositionWeightMatrix:
        """Create PWM object from matrix data"""
        matrix = motif_data.get('matrix', [])
        motif_id = motif_data.get('id', f"custom_{hash(str(matrix))}")
        
        # Generate consensus sequence
        consensus = ''
        for position in matrix:
            max_index = position.index(max(position))
            consensus += self.nucleotides[max_index]
        
        # Calculate information content
        info_content = self._calculate_information_content(matrix)
        
        return PositionWeightMatrix(
            motif_id=motif_id,
            matrix=matrix,
            length=len(matrix),
            consensus=consensus,
            information_content=info_content
        )
    
    def _calculate_information_content(self, matrix: List[List[float]]) -> List[float]:
        """Calculate information content for each position"""
        information_content = []
        
        for position in matrix:
            ic = 0
            for prob in position:
                if prob > 0:
                    ic += prob * math.log2(prob * 4)  # 4 nucleotides
            information_content.append(max(0, ic))  # Ensure non-negative
        
        return information_content
    
    def _compile_binding_site_summary(self, matches: List[MotifMatch], motifs: Dict[str, PositionWeightMatrix]) -> Dict:
        """Compile summary statistics for binding site results"""
        if not matches:
            return {"message": "No binding sites found"}
        
        # Group matches by motif
        motif_matches = defaultdict(list)
        for match in matches:
            motif_matches[match.motif_id].append(match)
        
        # Calculate statistics per motif
        motif_stats = {}
        for motif_id, motif_match_list in motif_matches.items():
            scores = [m.score for m in motif_match_list]
            
            motif_stats[motif_id] = {
                "total_matches": len(motif_match_list),
                "average_score": np.mean(scores),
                "max_score": max(scores),
                "min_score": min(scores),
                "consensus": motifs[motif_id].consensus if motif_id in motifs else "Unknown",
                "strand_distribution": {
                    "forward": len([m for m in motif_match_list if m.strand == '+']),
                    "reverse": len([m for m in motif_match_list if m.strand == '-'])
                }
            }
        
        return {
            "total_binding_sites": len(matches),
            "motifs_with_matches": len(motif_matches),
            "average_score_all": np.mean([m.score for m in matches]),
            "motif_statistics": motif_stats,
            "score_distribution": {
                "high_confidence": len([m for m in matches if m.score >= 0.9]),
                "medium_confidence": len([m for m in matches if 0.7 <= m.score < 0.9]),
                "low_confidence": len([m for m in matches if m.score < 0.7])
            }
        }
    
    async def create_custom_motif(self, sequences: List[str], motif_name: str) -> PositionWeightMatrix:
        """Create a PWM from a set of aligned binding sites"""
        if not sequences:
            raise ValueError("No sequences provided for motif creation")
        
        # Check that all sequences are the same length
        lengths = [len(seq) for seq in sequences]
        if len(set(lengths)) > 1:
            raise ValueError("All sequences must be the same length for motif creation")
        
        motif_length = lengths[0]
        
        # Count nucleotides at each position
        position_counts = []
        for i in range(motif_length):
            counts = {'A': 0, 'C': 0, 'G': 0, 'T': 0}
            for seq in sequences:
                nucleotide = seq[i].upper()
                if nucleotide in counts:
                    counts[nucleotide] += 1
            position_counts.append(counts)
        
        # Convert counts to probabilities with pseudocounts
        pseudocount = 1
        matrix = []
        for counts in position_counts:
            total = sum(counts.values()) + 4 * pseudocount
            probabilities = [
                (counts[nuc] + pseudocount) / total 
                for nuc in self.nucleotides
            ]
            matrix.append(probabilities)
        
        # Generate consensus
        consensus = ''
        for position in matrix:
            max_index = position.index(max(position))
            consensus += self.nucleotides[max_index]
        
        return PositionWeightMatrix(
            motif_id=motif_name,
            matrix=matrix,
            length=motif_length,
            consensus=consensus,
            information_content=self._calculate_information_content(matrix)
        )
    
    async def export_motif_results(self, matches: List[MotifMatch], format_type: str = "bed") -> str:
        """Export motif matches in various formats"""
        if format_type == "bed":
            return self._export_to_bed(matches)
        elif format_type == "gff":
            return self._export_to_gff(matches)
        elif format_type == "csv":
            return self._export_to_csv(matches)
        else:
            raise ValueError(f"Unsupported export format: {format_type}")
    
    def _export_to_bed(self, matches: List[MotifMatch]) -> str:
        """Export matches to BED format"""
        bed_lines = []
        bed_lines.append("track name=TFBS description='Transcription Factor Binding Sites'")
        
        for match in matches:
            line = f"{match.sequence_id}\t{match.start_position-1}\t{match.end_position}\t{match.motif_id}\t{int(match.score*1000)}\t{match.strand}"
            bed_lines.append(line)
        
        return '\n'.join(bed_lines)
    
    def _export_to_gff(self, matches: List[MotifMatch]) -> str:
        """Export matches to GFF format"""
        gff_lines = []
        gff_lines.append("##gff-version 3")
        
        for match in matches:
            attributes = f"ID=tfbs_{match.motif_id}_{match.start_position};Name={match.motif_id};score={match.score:.3f}"
            line = f"{match.sequence_id}\tTFBS_Scanner\ttranscription_factor_binding_site\t{match.start_position}\t{match.end_position}\t{match.score:.3f}\t{match.strand}\t.\t{attributes}"
            gff_lines.append(line)
        
        return '\n'.join(gff_lines)
    
    def _export_to_csv(self, matches: List[MotifMatch]) -> str:
        """Export matches to CSV format"""
        csv_lines = []
        csv_lines.append("sequence_id,motif_id,start_position,end_position,strand,score,sequence_match,p_value")
        
        for match in matches:
            line = f"{match.sequence_id},{match.motif_id},{match.start_position},{match.end_position},{match.strand},{match.score:.4f},{match.sequence_match},{match.p_value:.6f if match.p_value else 'NA'}"
            csv_lines.append(line)
        
        return '\n'.join(csv_lines)
    
    async def get_available_motifs(self, database: str = "builtin") -> Dict:
        """Get list of available motifs in database"""
        try:
            motifs = await self._get_motifs_from_database(database)
            
            motif_info = {}
            for motif_id, motif in motifs.items():
                motif_info[motif_id] = {
                    "consensus": motif.consensus,
                    "length": motif.length,
                    "information_content_sum": sum(motif.information_content)
                }
            
            return {
                "database": database,
                "motif_count": len(motifs),
                "motifs": motif_info
            }
            
        except Exception as e:
            logger.error(f"Error getting available motifs: {str(e)}")
            return {"error": f"Failed to get motifs: {str(e)}"}

# Global service instance
transcription_factor_service = TranscriptionFactorService()
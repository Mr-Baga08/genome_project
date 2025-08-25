# backend/app/services/data_converters.py
import io
import json
import re
from typing import List, Dict, Any, Optional
from fastapi import HTTPException
from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord

class DataConverterService:
    """Service for converting between different data formats"""
    
    @staticmethod
    async def format_converter(data: str, input_format: str, output_format: str) -> str:
        """Convert between different biological data formats"""
        try:
            # FASTA conversions
            if input_format.lower() == "fasta" and output_format.lower() == "genbank":
                records = SeqIO.parse(io.StringIO(data), "fasta")
                output = io.StringIO()
                for record in records:
                    # Convert to GenBank format (simplified)
                    output.write(f"LOCUS       {record.id}               {len(record.seq)} bp    DNA     linear   UNK\n")
                    output.write(f"DEFINITION  {record.description}\n")
                    output.write("ACCESSION   .\n")
                    output.write("VERSION     .\n")
                    output.write("KEYWORDS    .\n")
                    output.write("SOURCE      .\n")
                    output.write("ORIGIN\n")
                    
                    # Write sequence in blocks of 60 with position numbers
                    sequence = str(record.seq).lower()
                    for i in range(0, len(sequence), 60):
                        line_num = str(i + 1).rjust(9)
                        sequence_line = sequence[i:i+60]
                        # Format in blocks of 10
                        formatted_line = " ".join([sequence_line[j:j+10] for j in range(0, len(sequence_line), 10)])
                        output.write(f"{line_num} {formatted_line}\n")
                    
                    output.write("//\n")
                return output.getvalue()
                
            elif input_format.lower() == "genbank" and output_format.lower() == "fasta":
                records = SeqIO.parse(io.StringIO(data), "genbank")
                output = io.StringIO()
                for record in records:
                    output.write(f">{record.id} {record.description}\n{record.seq}\n")
                return output.getvalue()
                
            elif input_format.lower() == "fastq" and output_format.lower() == "fasta":
                records = SeqIO.parse(io.StringIO(data), "fastq")
                output = io.StringIO()
                for record in records:
                    output.write(f">{record.id}\n{record.seq}\n")
                return output.getvalue()
                
            elif input_format.lower() == "gff3" and output_format.lower() == "bed":
                return DataConverterService._gff3_to_bed(data)
                
            elif input_format.lower() == "bed" and output_format.lower() == "gff3":
                return DataConverterService._bed_to_gff3(data)
                
            elif input_format.lower() == "vcf" and output_format.lower() == "bed":
                return DataConverterService._vcf_to_bed(data)
                
            elif input_format.lower() == "csv" and output_format.lower() == "json":
                return DataConverterService._csv_to_json(data)
                
            elif input_format.lower() == "json" and output_format.lower() == "csv":
                return DataConverterService._json_to_csv(data)
                
            else:
                raise HTTPException(status_code=400, detail=f"Conversion from {input_format} to {output_format} not supported")
                
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Conversion error: {str(e)}")
    
    @staticmethod
    async def json_parser(json_data: str, data_type: str) -> List[Dict]:
        """Parse JSON data into biological data structures"""
        try:
            parsed_data = json.loads(json_data)
            
            if data_type == "sequences":
                return DataConverterService._parse_sequence_json(parsed_data)
            elif data_type == "annotations":
                return DataConverterService._parse_annotation_json(parsed_data)
            elif data_type == "variants":
                return DataConverterService._parse_variant_json(parsed_data)
            elif data_type == "reads":
                return DataConverterService._parse_reads_json(parsed_data)
            elif data_type == "alignments":
                return DataConverterService._parse_alignment_json(parsed_data)
            else:
                return parsed_data if isinstance(parsed_data, list) else [parsed_data]
                
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"JSON parsing error: {str(e)}")

    @staticmethod
    async def sequence_converter(sequences: List[Dict], conversion_type: str, parameters: Dict = None) -> List[Dict]:
        """Convert sequences between different types and formats"""
        try:
            if parameters is None:
                parameters = {}
            
            converted_sequences = []
            
            for seq in sequences:
                sequence_data = seq.get('sequence', '')
                converted_seq = seq.copy()
                
                if conversion_type == "dna_to_rna":
                    # Convert DNA to RNA (T -> U)
                    converted_seq['sequence'] = sequence_data.replace('T', 'U').replace('t', 'u')
                    converted_seq['sequence_type'] = 'RNA'
                    
                elif conversion_type == "rna_to_dna":
                    # Convert RNA to DNA (U -> T)
                    converted_seq['sequence'] = sequence_data.replace('U', 'T').replace('u', 't')
                    converted_seq['sequence_type'] = 'DNA'
                    
                elif conversion_type == "reverse_complement":
                    # Calculate reverse complement
                    complement_map = {'A': 'T', 'T': 'A', 'G': 'C', 'C': 'G', 'N': 'N'}
                    reverse_comp = ''.join(complement_map.get(base.upper(), base) for base in reversed(sequence_data))
                    converted_seq['sequence'] = reverse_comp
                    converted_seq['id'] = f"{seq.get('id', '')}_rc"
                    
                elif conversion_type == "translate":
                    # Translate DNA/RNA to protein
                    translated = DataConverterService._translate_sequence(sequence_data, parameters)
                    converted_seq['sequence'] = translated
                    converted_seq['sequence_type'] = 'PROTEIN'
                    converted_seq['id'] = f"{seq.get('id', '')}_translated"
                    
                elif conversion_type == "uppercase":
                    converted_seq['sequence'] = sequence_data.upper()
                    
                elif conversion_type == "lowercase":
                    converted_seq['sequence'] = sequence_data.lower()
                    
                elif conversion_type == "remove_gaps":
                    converted_seq['sequence'] = sequence_data.replace('-', '').replace('.', '')
                    
                elif conversion_type == "mask_lowercase":
                    # Convert lowercase to N (masking)
                    masked_seq = ''.join('N' if c.islower() else c for c in sequence_data)
                    converted_seq['sequence'] = masked_seq
                
                else:
                    raise ValueError(f"Unknown conversion type: {conversion_type}")
                
                converted_sequences.append(converted_seq)
            
            return converted_sequences
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error converting sequences: {str(e)}")

    @staticmethod
    def _gff3_to_bed(gff3_data: str) -> str:
        """Convert GFF3 to BED format"""
        output = io.StringIO()
        for line in gff3_data.strip().split('\n'):
            if line.startswith('#') or not line.strip():
                continue
            
            parts = line.split('\t')
            if len(parts) >= 9:
                # BED format: chrom, start, end, name, score, strand
                bed_line = f"{parts[0]}\t{int(parts[3])-1}\t{parts[4]}\t{parts[2]}\t{parts[5] if parts[5] != '.' else '0'}\t{parts[6]}\n"
                output.write(bed_line)
        
        return output.getvalue()
    
    @staticmethod
    def _bed_to_gff3(bed_data: str) -> str:
        """Convert BED to GFF3 format"""
        output = io.StringIO()
        output.write("##gff-version 3\n")
        
        for line in bed_data.strip().split('\n'):
            if line.startswith('#') or not line.strip():
                continue
            
            parts = line.split('\t')
            if len(parts) >= 3:
                # GFF3 format: seqid, source, type, start, end, score, strand, phase, attributes
                gff3_line = f"{parts[0]}\tbed_convert\tfeature\t{int(parts[1])+1}\t{parts[2]}\t{parts[4] if len(parts) > 4 else '.'}\t{parts[5] if len(parts) > 5 else '.'}\t.\tName={parts[3] if len(parts) > 3 else 'feature'}\n"
                output.write(gff3_line)
        
        return output.getvalue()

    @staticmethod
    def _vcf_to_bed(vcf_data: str) -> str:
        """Convert VCF to BED format"""
        output = io.StringIO()
        
        for line in vcf_data.strip().split('\n'):
            if line.startswith('#') or not line.strip():
                continue
            
            parts = line.split('\t')
            if len(parts) >= 8:
                # BED format for variants
                chrom = parts[0]
                pos = int(parts[1])
                end_pos = pos + len(parts[3])  # REF length
                variant_id = parts[2] if parts[2] != '.' else f"var_{pos}"
                
                bed_line = f"{chrom}\t{pos-1}\t{end_pos}\t{variant_id}\t{parts[5] if parts[5] != '.' else '0'}\t.\n"
                output.write(bed_line)
        
        return output.getvalue()

    @staticmethod
    def _csv_to_json(csv_data: str) -> str:
        """Convert CSV to JSON format"""
        import csv
        
        reader = csv.DictReader(io.StringIO(csv_data))
        data = list(reader)
        return json.dumps(data, indent=2)

    @staticmethod
    def _json_to_csv(json_data: str) -> str:
        """Convert JSON to CSV format"""
        data = json.loads(json_data)
        
        if not isinstance(data, list):
            data = [data]
        
        if not data:
            return ""
        
        output = io.StringIO()
        fieldnames = data[0].keys()
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
        
        return output.getvalue()

    @staticmethod
    def _translate_sequence(sequence: str, parameters: Dict) -> str:
        """Translate DNA/RNA sequence to protein"""
        from Bio.Seq import Seq
        
        table = parameters.get('translation_table', 1)  # Standard genetic code
        reading_frame = parameters.get('reading_frame', 1)  # 1, 2, or 3
        
        # Adjust sequence for reading frame
        seq_obj = Seq(sequence[reading_frame-1:])
        
        # Translate
        protein = seq_obj.translate(table=table, stop_symbol='*')
        
        return str(protein)

    @staticmethod
    def _parse_sequence_json(json_data: Any) -> List[Dict]:
        """Parse JSON into sequence format"""
        if isinstance(json_data, dict):
            if 'sequences' in json_data:
                return json_data['sequences']
            elif 'data' in json_data:
                return json_data['data']
            else:
                return [json_data]
        elif isinstance(json_data, list):
            return json_data
        else:
            return [{"sequence": str(json_data), "id": "parsed_sequence"}]
    
    @staticmethod
    def _parse_annotation_json(json_data: Any) -> List[Dict]:
        """Parse JSON into annotation format"""
        if isinstance(json_data, dict):
            if 'features' in json_data:
                return json_data['features']
            elif 'annotations' in json_data:
                return json_data['annotations']
            else:
                return [json_data]
        elif isinstance(json_data, list):
            return json_data
        else:
            return [json_data]
    
    @staticmethod
    def _parse_variant_json(json_data: Any) -> List[Dict]:
        """Parse JSON into variant format"""
        if isinstance(json_data, dict):
            if 'variants' in json_data:
                return json_data['variants']
            elif 'calls' in json_data:
                return json_data['calls']
            else:
                return [json_data]
        elif isinstance(json_data, list):
            return json_data
        else:
            return [json_data]

    @staticmethod
    def _parse_reads_json(json_data: Any) -> List[Dict]:
        """Parse JSON into reads format"""
        if isinstance(json_data, dict):
            if 'reads' in json_data:
                return json_data['reads']
            elif 'sequences' in json_data:
                return json_data['sequences']
            else:
                return [json_data]
        elif isinstance(json_data, list):
            return json_data
        else:
            return [json_data]

    @staticmethod
    def _parse_alignment_json(json_data: Any) -> List[Dict]:
        """Parse JSON into alignment format"""
        if isinstance(json_data, dict):
            if 'alignment' in json_data:
                return json_data['alignment']
            elif 'aligned_sequences' in json_data:
                return json_data['aligned_sequences']
            else:
                return [json_data]
        elif isinstance(json_data, list):
            return json_data
        else:
            return [json_data]

    @staticmethod
    async def coordinate_converter(coordinates: List[Dict], conversion_type: str) -> List[Dict]:
        """Convert between different coordinate systems"""
        try:
            converted = []
            
            for coord in coordinates:
                converted_coord = coord.copy()
                
                if conversion_type == "0_to_1_based":
                    # Convert 0-based to 1-based coordinates
                    converted_coord['start'] = coord.get('start', 0) + 1
                    
                elif conversion_type == "1_to_0_based":
                    # Convert 1-based to 0-based coordinates
                    converted_coord['start'] = max(0, coord.get('start', 1) - 1)
                    
                elif conversion_type == "bed_to_gff":
                    # BED (0-based, half-open) to GFF (1-based, closed)
                    converted_coord['start'] = coord.get('start', 0) + 1
                    # end stays the same for BED to GFF conversion
                    
                elif conversion_type == "gff_to_bed":
                    # GFF (1-based, closed) to BED (0-based, half-open)
                    converted_coord['start'] = max(0, coord.get('start', 1) - 1)
                    # end stays the same for GFF to BED conversion
                
                converted.append(converted_coord)
            
            return converted
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error converting coordinates: {str(e)}")

    @staticmethod
    async def text_to_sequence(text_data: str, parameters: Dict = None) -> List[Dict]:
        """Convert plain text to sequence format"""
        try:
            if parameters is None:
                parameters = {}
            
            sequences = []
            
            # Remove whitespace and newlines
            clean_text = re.sub(r'\s+', '', text_data.upper())
            
            # Validate as biological sequence
            valid_dna = set('ATCGRYSWKMBDHVN')
            valid_protein = set('ACDEFGHIKLMNPQRSTVWY*')
            
            sequence_type = "DNA"
            if set(clean_text).issubset(valid_dna):
                sequence_type = "DNA"
            elif set(clean_text).issubset(valid_protein):
                sequence_type = "PROTEIN"
            else:
                # Try to clean invalid characters
                if parameters.get('remove_invalid_chars', False):
                    clean_text = re.sub(r'[^ATCGRYSWKMBDHVN]', '', clean_text)
                    sequence_type = "DNA"
                else:
                    raise ValueError("Text contains invalid sequence characters")
            
            sequences.append({
                "id": parameters.get('sequence_id', 'text_sequence'),
                "sequence": clean_text,
                "sequence_type": sequence_type,
                "length": len(clean_text),
                "description": parameters.get('description', 'Converted from text')
            })
            
            return sequences
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error converting text to sequence: {str(e)}")

    @staticmethod
    async def reverse_complement(sequences: List[Dict]) -> List[Dict]:
        """Calculate reverse complement of DNA sequences"""
        try:
            result = []
            
            for seq in sequences:
                sequence_data = seq.get('sequence', '').upper()
                
                # Check if it's DNA
                if seq.get('sequence_type', 'DNA') not in ['DNA', 'RNA']:
                    raise ValueError(f"Cannot reverse complement non-nucleotide sequence: {seq.get('id', '')}")
                
                # Complement mapping
                if seq.get('sequence_type', 'DNA') == 'DNA':
                    complement = {'A': 'T', 'T': 'A', 'C': 'G', 'G': 'C', 'N': 'N', 'R': 'Y', 'Y': 'R', 'S': 'S', 'W': 'W', 'K': 'M', 'M': 'K', 'B': 'V', 'D': 'H', 'H': 'D', 'V': 'B'}
                else:  # RNA
                    complement = {'A': 'U', 'U': 'A', 'C': 'G', 'G': 'C', 'N': 'N', 'R': 'Y', 'Y': 'R', 'S': 'S', 'W': 'W', 'K': 'M', 'M': 'K', 'B': 'V', 'D': 'H', 'H': 'D', 'V': 'B'}
                
                reverse_comp = ''.join(complement.get(base, base) for base in reversed(sequence_data))
                
                result_seq = seq.copy()
                result_seq['sequence'] = reverse_comp
                result_seq['id'] = f"{seq.get('id', '')}_rc"
                result_seq['description'] = f"Reverse complement of {seq.get('description', seq.get('id', ''))}"
                
                result.append(result_seq)
            
            return result
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error calculating reverse complement: {str(e)}")

    @staticmethod
    async def split_assembly_into_sequences(assembly_data: Dict) -> List[Dict]:
        """Split assembly data into individual sequences"""
        try:
            sequences = []
            
            if 'contigs' in assembly_data:
                for i, contig in enumerate(assembly_data['contigs']):
                    sequences.append({
                        "id": contig.get('id', f"contig_{i+1}"),
                        "sequence": contig.get('sequence', ''),
                        "length": contig.get('length', len(contig.get('sequence', ''))),
                        "description": f"Contig from assembly",
                        "assembly_info": {
                            "coverage": contig.get('coverage', 0),
                            "gc_content": DataFlowService._calculate_gc_content(contig.get('sequence', ''))
                        }
                    })
            elif 'sequences' in assembly_data:
                sequences = assembly_data['sequences']
            else:
                # Assume assembly_data is already a list of sequences
                sequences = assembly_data if isinstance(assembly_data, list) else [assembly_data]
            
            return sequences
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error splitting assembly: {str(e)}")

    @staticmethod
    async def bedgraph_to_bigwig(bedgraph_data: str, chrom_sizes: Dict[str, int]) -> bytes:
        """Convert bedGraph to bigWig format (placeholder implementation)"""
        try:
            # This would require proper bigWig library integration
            # For now, return the bedGraph data as binary
            return bedgraph_data.encode('utf-8')
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error converting bedGraph to bigWig: {str(e)}")

    # Helper methods for DataFlowService (moved here for access)
    @staticmethod
    def _calculate_gc_content(sequence: str) -> float:
        """Calculate GC content of sequence"""
        if not sequence:
            return 0.0
        gc_count = sequence.upper().count('G') + sequence.upper().count('C')
        return (gc_count / len(sequence)) * 100
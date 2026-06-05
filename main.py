from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Any, Callable, Dict, List, TypedDict, cast


from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import ListProperty, StringProperty
from kivy.uix.modalview import ModalView
from kivymd.uix.card import MDCard
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.dialog import MDDialog
from kivymd.toast import toast
from kivymd.uix.datatables import MDDataTable
from kivymd.uix.textfield import MDTextField

from core.alignment import needleman_wunsch
from core.dna_analyzer import analyze_sequence
from core.disease_facts import get_disease_facts
from core.fasta_parser import parse_multi_fasta
from core.ncbi_api import get_cached_disease_profile, search_local_disease_gene, search_ncbi_gene_bundle
from database.storage import (
    fetch_bookmarked_gene_by_id,
    fetch_bookmarked_genes,
    fetch_recent_history,
    fetch_saved_sequence_by_id,
    fetch_saved_sequences,
    init_database,
    log_search,
    save_bookmarked_gene,
    save_sequence_record,
)


BASE_DIR = Path(__file__).resolve().parent
UI_DIR = BASE_DIR / "ui"
ASSETS_DIR = BASE_DIR / "assets"
PIE_CHART_PATH = ASSETS_DIR / "nucleotide_pie.png"


class MetricCard(MDCard):
    title = StringProperty("")
    value = StringProperty("")
    value_color = ListProperty([1, 1, 1, 1])


class InfoCard(MDCard):
    title = StringProperty("")
    body = StringProperty("")


class FormDialogContent(MDBoxLayout):
    pass


def load_local_env() -> None:
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


class BioExplorerApp(MDApp):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.last_analysis: Dict[str, Any] | None = None
        self.last_gene_bundle: Dict[str, Any] | None = None
        self.loaded_sequences: List[Dict[str, str]] = []
        self.last_alignment: Dict[str, Any] | None = None
        self._active_dialog: MDDialog | None = None
        self._table_rows_by_id: Dict[str, Dict[int, Dict[str, Any]]] = {}

    def build(self) -> Any:
        load_local_env()
        init_database()
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "DeepPurple"
        Builder.load_file(str(UI_DIR / "widgets.kv"))
        return Builder.load_file(str(UI_DIR / "dashboard.kv"))

    def on_start(self) -> None:
        self.root.ids.status_label.text = "Ready"
        self.analyze_sequence_action()

    def toggle_drawer(self) -> None:
        self.root.ids.nav_drawer.set_state("toggle")

    def analyze_sequence_action(self) -> None:
        sequence = self.root.ids.sequence_input.text.strip()
        if not sequence:
            toast("Paste a DNA or FASTA sequence first.")
            return
        try:
            self.loaded_sequences = parse_multi_fasta(sequence)
        except Exception as exc:
            self._set_status(f"FASTA parsing failed: {exc}")
            return

        self.root.ids.status_label.text = "Analyzing sequence..."
        threading.Thread(target=self._analyze_worker, args=(sequence,), daemon=True).start()

    def _analyze_worker(self, sequence: str) -> None:
        try:
            result = analyze_sequence(sequence, str(PIE_CHART_PATH))
        except Exception as exc:
            message = f"Analysis failed: {exc}"
            Clock.schedule_once(lambda _dt, msg=message: self._set_status(msg))
            return
        Clock.schedule_once(lambda _dt: self._apply_analysis_result(result))

    def _apply_analysis_result(self, result: Dict[str, Any]) -> None:
        self.last_analysis = result
        ids = self.root.ids
        ids.sequence_title.text = result.get("fasta_header") or "Raw DNA Sequence"
        ids.sequence_visualization.text = self._format_sequence_visualization(result)
        ids.length_card.value = f"{result['length']} bp"
        ids.gc_card.value = f"{result['gc_content']}%"
        ids.weight_card.value = f"{result['molecular_weight']}"
        ids.reverse_card.body = str(result["reverse_complement"])
        protein_text = str(result["protein"]) or "-"
        if result.get("warning"):
            protein_text = f"{protein_text}\n{result['warning']}"
        ids.protein_card.body = protein_text

        counts = result["nucleotide_counts"]
        percentages = result["nucleotide_percentages"]
        ids.a_card.value = f"{counts['A']} ({percentages['A']}%)"
        ids.t_card.value = f"{counts['T']} ({percentages['T']}%)"
        ids.g_card.value = f"{counts['G']} ({percentages['G']}%)"
        ids.c_card.value = f"{counts['C']} ({percentages['C']}%)"

        ids.pie_chart.reload()
        if len(self.loaded_sequences) >= 2:
            self.run_alignment_action(auto=True)
        else:
            ids.alignment_title.text = "Alignment Viewer"
            ids.alignment_body.text = "Load a multi-sequence FASTA file with 2 or more sequences to run alignment."
            ids.alignment_stats.text = "Identity: - | Score: -"
        ids.status_label.text = "Sequence analysis complete."

    def upload_fasta_action(self) -> None:
        try:
            import tkinter as tk
            from tkinter import filedialog

            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            file_path = filedialog.askopenfilename(
                title="Select FASTA File",
                filetypes=[
                    ("FASTA files", "*.fasta *.fa *.fna *.ffn *.faa *.frn"),
                    ("Text files", "*.txt"),
                    ("All files", "*.*"),
                ],
            )
            root.destroy()
        except Exception as exc:
            self.root.ids.status_label.text = f"File picker failed: {exc}"
            return

        if not file_path:
            self.root.ids.status_label.text = "FASTA upload cancelled."
            return

        try:
            sequence_text = Path(file_path).read_text(encoding="utf-8")
        except Exception as exc:
            self.root.ids.status_label.text = f"Could not read file: {exc}"
            return

        self.root.ids.sequence_input.text = sequence_text
        self.root.ids.status_label.text = f"Loaded FASTA file: {Path(file_path).name}"
        self.analyze_sequence_action()

    def search_gene_action(self) -> None:
        query = self.root.ids.search_input.text.strip()
        if not query:
            toast("Enter a disease or gene query first.")
            return

        self.root.ids.status_label.text = "Searching local and NCBI data..."
        threading.Thread(target=self._search_worker, args=(query,), daemon=True).start()

    def _search_worker(self, query: str) -> None:
        try:
            disease_profile = get_cached_disease_profile(query)
            local_results = cast(List[Dict[str, Any]], disease_profile.get("local_results", []))
            ncbi_bundle = {
                "disease_profile": disease_profile,
                "genes": disease_profile.get("genes", []),
                "proteins": disease_profile.get("proteins", []),
                "related_diseases": disease_profile.get("related_diseases", []),
                "summary": disease_profile.get("summary", ""),
                "medgen_ids": disease_profile.get("medgen_ids", []),
                "medgen_links": disease_profile.get("medgen_links", []),
                "medlineplus": disease_profile.get("medlineplus", {}),
                "clinical_sections": disease_profile.get("clinical_sections", {}),
                "sources": disease_profile.get("sources", {}),
                "disease_type": disease_profile.get("disease_type"),
            }
            log_search("local_disease_gene", query, len(local_results))
            log_search("ncbi_gene", query, len(ncbi_bundle["genes"]))
        except Exception as exc:
            message = f"Search failed: {exc}"
            Clock.schedule_once(lambda _dt, msg=message: self._set_status(msg))
            return
        Clock.schedule_once(lambda _dt: self._apply_search_result(query, local_results, ncbi_bundle))

    def _apply_search_result(self, query: str, local_results: List[Dict[str, Any]], ncbi_bundle: Dict[str, Any]) -> None:
        self.last_gene_bundle = ncbi_bundle
        ids = self.root.ids

        if local_results:
            top_local = local_results[0]
            ids.local_gene_title.text = top_local["disease"]
            ids.local_gene_body.text = (
                f"Genes: {', '.join(top_local['genes'])}\n"
                f"Matched by: {', '.join(top_local['matched_by'])}\n\n"
                f"{top_local['description']}"
            )
        else:
            ids.local_gene_title.text = f"Disease profile: {query}"
            ids.local_gene_body.text = str(ncbi_bundle.get("summary") or f"No local disease match found for {query}.")

        genes = ncbi_bundle["genes"]
        proteins = ncbi_bundle["proteins"]
        related_diseases = ncbi_bundle["related_diseases"]
        disease_facts = cast(Dict[str, Any], ncbi_bundle.get("disease_profile", {}).get("disease_facts")) or get_disease_facts(query, related_diseases)
        medlineplus = cast(Dict[str, Any], ncbi_bundle.get("medlineplus", {}))
        clinical_sections = cast(Dict[str, Any], ncbi_bundle.get("clinical_sections", {}))
        medgen_links = cast(List[str], ncbi_bundle.get("medgen_links", []))

        if genes:
            top_gene = genes[0]
            ids.ncbi_gene_title.text = f"{top_gene['symbol']} ({top_gene['gene_id']})"
            ids.ncbi_gene_body.text = (
                f"{top_gene['official_name']}\n\n"
                f"{top_gene['summary'] or 'No summary available.'}\n\n"
                f"Organism: {top_gene['organism']}\n"
                f"Chromosome: {top_gene['chromosome']}\n"
                f"Map location: {top_gene['map_location']}"
            )
            ids.external_links.text = f"NCBI Gene: {top_gene['ncbi_url']}"
        else:
            medgen_ids = ncbi_bundle.get("medgen_ids", [])
            ids.ncbi_gene_title.text = f"NCBI Disease Cache: {query}"
            ids.ncbi_gene_body.text = (
                f"Disease search cached locally.\n\n"
                f"MedGen IDs: {', '.join(medgen_ids) if medgen_ids else 'No MedGen concept found.'}\n\n"
                f"{ncbi_bundle.get('summary') or 'No NCBI gene result found.'}"
            )
            ids.external_links.text = "-"

        ids.related_diseases.text = ", ".join(related_diseases) if related_diseases else "No related local disease links found."
        if proteins:
            ids.protein_info.text = "\n".join(
                f"- {item['caption']} ({item['accession_version']})\n  {item['title']}" for item in proteins[:4]
            )
        else:
            ids.protein_info.text = "No related protein entries found."

        external_lines: List[str] = []
        if genes:
            external_lines.append(f"NCBI Gene: {genes[0]['ncbi_url']}")
        if medlineplus.get("url"):
            external_lines.append(f"MedlinePlus: {medlineplus['url']}")
        if medgen_links:
            external_lines.append(f"MedGen: {medgen_links[0]}")
        source_links = cast(Dict[str, str], ncbi_bundle.get("sources", {}))
        if source_links.get("medgen_overview"):
            external_lines.append(f"MedGen Overview: {source_links['medgen_overview']}")
        if source_links.get("medlineplus_connect_technical"):
            external_lines.append(f"MedlinePlus Tech: {source_links['medlineplus_connect_technical']}")
        ids.external_links.text = "\n".join(external_lines) if external_lines else "-"

        genetic_flag = ncbi_bundle.get("disease_type", disease_facts.get("is_genetic"))
        if genetic_flag is True:
            ids.disease_type_label.text = "Disease Type: Genetic / Hereditary association present"
        elif genetic_flag is False:
            ids.disease_type_label.text = "Disease Type: Not strictly genetic only; may be multifactorial or acquired"
        else:
            ids.disease_type_label.text = "Disease Type: Not yet classified in local disease facts cache"

        symptoms = cast(List[str], clinical_sections.get("symptoms", disease_facts.get("symptoms", [])))
        precautions = cast(List[str], clinical_sections.get("precautions", disease_facts.get("precautions", [])))
        treatment = cast(List[str], clinical_sections.get("treatment", disease_facts.get("treatment", [])))

        ids.symptoms_body.text = "\n".join(f"- {item}" for item in symptoms)
        ids.precautions_body.text = "\n".join(f"- {item}" for item in precautions)
        ids.treatment_body.text = "\n".join(f"- {item}" for item in treatment)
        ids.ai_explanation_body.text = self._build_ai_explanation(
            query=query,
            disease_facts=disease_facts,
            local_results=local_results,
            genes=genes,
            disease_profile=cast(Dict[str, Any], ncbi_bundle.get("disease_profile", {})),
        )

        ids.status_label.text = "Disease / gene search complete."

    def run_alignment_action(self, auto: bool = False) -> None:
        if len(self.loaded_sequences) < 2:
            if not auto:
                toast("Load or paste at least 2 FASTA sequences for alignment.")
            return
        seq1 = self.loaded_sequences[0]
        seq2 = self.loaded_sequences[1]
        result = needleman_wunsch(seq1["sequence"], seq2["sequence"])
        self.last_alignment = result
        self.root.ids.alignment_title.text = f"Alignment: {seq1['header']} vs {seq2['header']}"
        self.root.ids.alignment_body.text = self._format_alignment_markup(result)
        self.root.ids.alignment_stats.text = f"Identity: {result['identity_percent']}% | Score: {result['score']}"
        if not auto:
            self.root.ids.status_label.text = "Alignment complete."

    def save_sequence_action(self) -> None:
        if not self.last_analysis:
            toast("Analyze a sequence before saving it.")
            return
        default_label = str(self.last_analysis.get("fasta_header") or "Sequence Record")
        content = FormDialogContent(orientation="vertical", spacing="12dp", size_hint_y=None)
        content.bind(minimum_height=content.setter("height"))
        label_field = MDTextField(text=default_label, hint_text="Sequence label", mode="rectangle")
        notes_field = MDTextField(text="", hint_text="Notes", mode="rectangle", multiline=True, size_hint_y=None, height="120dp")
        content.add_widget(label_field)
        content.add_widget(notes_field)

        def submit_save(*_args: Any) -> None:
            sequence_text = self.root.ids.sequence_input.text.strip()
            label = label_field.text.strip() or default_label
            notes = notes_field.text.strip()
            record_id = save_sequence_record(
                label=label,
                sequence=sequence_text,
                notes=notes,
                analysis=self.last_analysis or {},
            )
            self._dismiss_dialog()
            self.root.ids.status_label.text = f"Sequence saved with id {record_id}."
            toast("Sequence saved.")

        self._open_dialog(
            "Save Sequence",
            content,
            submit_save,
            save_text="Save",
        )

    def bookmark_gene_action(self) -> None:
        if not self.last_gene_bundle or not self.last_gene_bundle["genes"]:
            toast("Search a gene before bookmarking it.")
            return
        gene = self.last_gene_bundle["genes"][0]
        content = FormDialogContent(orientation="vertical", spacing="12dp", size_hint_y=None)
        content.bind(minimum_height=content.setter("height"))
        symbol_field = MDTextField(text=str(gene.get("symbol", "")), hint_text="Gene symbol", mode="rectangle")
        name_field = MDTextField(text=str(gene.get("official_name", "")), hint_text="Official name", mode="rectangle")
        notes_field = MDTextField(
            text=str(gene.get("summary", ""))[:400],
            hint_text="Short note / summary",
            mode="rectangle",
            multiline=True,
            size_hint_y=None,
            height="140dp",
        )
        content.add_widget(symbol_field)
        content.add_widget(name_field)
        content.add_widget(notes_field)

        def submit_bookmark(*_args: Any) -> None:
            payload = dict(gene)
            payload["symbol"] = symbol_field.text.strip() or str(gene.get("symbol", ""))
            payload["official_name"] = name_field.text.strip() or str(gene.get("official_name", ""))
            payload["summary"] = notes_field.text.strip() or str(gene.get("summary", ""))
            record_id = save_bookmarked_gene(payload)
            self._dismiss_dialog()
            self.root.ids.status_label.text = f"Gene bookmarked with id {record_id}."
            toast("Gene bookmarked.")

        self._open_dialog(
            "Bookmark Gene",
            content,
            submit_bookmark,
            save_text="Bookmark",
        )

    def show_history_action(self) -> None:
        history_records = fetch_recent_history(15)
        self._table_rows_by_id["history"] = {int(row["id"]): row for row in history_records}
        self._open_table_modal(
            "Search History",
            [("ID", 12), ("Type", 30), ("Query", 44), ("Count", 16), ("Created", 34)],
            [(str(row["id"]), row["search_type"], row["query"], str(row["result_count"]), row["created_at"]) for row in history_records],
            "history",
        )

    def show_saved_sequences_action(self) -> None:
        saved_rows = fetch_saved_sequences(15)
        self._table_rows_by_id["saved"] = {int(row["id"]): row for row in saved_rows}
        self._open_table_modal(
            "Saved Sequences",
            [("ID", 12), ("Label", 28), ("Header", 28), ("Length", 14), ("GC %", 14), ("Created", 28)],
            [
                (
                    str(row["id"]),
                    row["label"],
                    row["fasta_header"] or "-",
                    str(row["length"]),
                    str(row["gc_content"]),
                    row["created_at"],
                )
                for row in saved_rows
            ],
            "saved",
        )

    def show_bookmarks_action(self) -> None:
        bookmark_rows = fetch_bookmarked_genes(15)
        self._table_rows_by_id["bookmarks"] = {int(row["id"]): row for row in bookmark_rows}
        self._open_table_modal(
            "Bookmarked Genes",
            [("ID", 12), ("Symbol", 18), ("Gene ID", 16), ("Official Name", 42), ("Created", 28)],
            [
                (
                    str(row["id"]),
                    row["symbol"],
                    row["gene_id"],
                    row["official_name"],
                    row["created_at"],
                )
                for row in bookmark_rows
            ],
            "bookmarks",
        )

    def _open_table_modal(
        self,
        title: str,
        columns: List[tuple[str, int]],
        rows: List[tuple[Any, ...]],
        table_key: str,
    ) -> None:
        modal = ModalView(size_hint=(0.92, 0.84), auto_dismiss=True)
        placeholder = tuple("-" for _ in columns)
        table = MDDataTable(
            size_hint=(1, 1),
            use_pagination=True,
            rows_num=10,
            column_data=columns,
            row_data=rows or [placeholder],
        )
        table.bind(
            on_row_press=lambda instance, row: self._handle_table_row_press(
                table_key,
                table,
                row,
                modal,
                len(columns),
            )
        )
        modal.add_widget(table)
        modal.open()
        self.root.ids.status_label.text = f"Viewing {title.lower()}."

    def _handle_table_row_press(
        self,
        table_key: str,
        table: MDDataTable,
        row: Any,
        modal: ModalView,
        column_count: int,
    ) -> None:
        record_id = self._extract_record_id_from_row(table, row, column_count)
        if record_id is None:
            return
        modal.dismiss()

        if table_key == "history":
            record = self._table_rows_by_id.get("history", {}).get(record_id)
            if not record:
                return
            self.root.ids.search_input.text = str(record["query"])
            self.root.ids.status_label.text = f"Loaded history query: {record['query']}. Running search..."
            self.search_gene_action()
            return

        if table_key == "saved":
            record = fetch_saved_sequence_by_id(record_id)
            if not record:
                return
            self.root.ids.sequence_input.text = str(record["sequence"])
            self.root.ids.sequence_title.text = str(record["label"])
            self.root.ids.status_label.text = f"Loaded saved sequence: {record['label']}. Running analysis..."
            toast("Saved sequence loaded.")
            self.analyze_sequence_action()
            return

        if table_key == "bookmarks":
            record = fetch_bookmarked_gene_by_id(record_id)
            if not record:
                return
            self.root.ids.search_input.text = str(record["symbol"])
            self.root.ids.status_label.text = f"Loaded bookmarked gene: {record['symbol']}. Running search..."
            toast("Bookmarked gene loaded.")
            self.search_gene_action()

    def _extract_record_id_from_row(
        self,
        table: MDDataTable,
        row: Any,
        column_count: int,
    ) -> int | None:
        row_index = getattr(row, "index", None)
        if isinstance(row_index, int) and column_count > 0:
            data_index = row_index // column_count
            if 0 <= data_index < len(table.row_data):
                raw_id = table.row_data[data_index][0]
                if str(raw_id).isdigit():
                    return int(str(raw_id))

        row_text = getattr(row, "text", "")
        if str(row_text).isdigit():
            return int(str(row_text))
        return None

    def _open_dialog(
        self,
        title: str,
        content: MDBoxLayout,
        submit_callback: Callable[..., None],
        save_text: str = "Save",
    ) -> None:
        self._dismiss_dialog()
        self._active_dialog = MDDialog(
            title=title,
            type="custom",
            content_cls=content,
            buttons=[
                MDFlatButton(text="Cancel", on_release=lambda *_args: self._dismiss_dialog()),
                MDRaisedButton(text=save_text, on_release=submit_callback),
            ],
        )
        self._active_dialog.open()

    def _dismiss_dialog(self) -> None:
        if self._active_dialog is not None:
            self._active_dialog.dismiss()
            self._active_dialog = None

    def _format_sequence_visualization(self, result: Dict[str, Any]) -> str:
        raw_sequence = self.root.ids.sequence_input.text.strip()
        lines = [line.strip() for line in raw_sequence.splitlines() if line.strip() and not line.startswith(">")]
        sequence = "".join(lines)
        if not sequence:
            return "No sequence loaded."

        color_map = {"A": "#4DA3FF", "T": "#FFD34D", "G": "#3CE58E", "C": "#7E7BFF"}
        limited_sequence = sequence[:160]
        colored = [f"[color={color_map.get(base, '#FFFFFF')}]{base}[/color]" for base in limited_sequence]
        chunked = ["".join(colored[index : index + 10]) for index in range(0, len(colored), 10)]
        grouped_lines = [" ".join(chunked[index : index + 4]) for index in range(0, len(chunked), 4)]
        header = result.get("fasta_header") or "Sequence preview"
        return (
            f"{header}\n\n"
            f"Length: {result['length']} bp | GC: {result['gc_content']}% | Codons: {result['complete_codons']}\n\n"
            + "\n".join(grouped_lines)
            + ("\n..." if len(sequence) > 160 else "")
        )

    def _format_alignment_markup(self, result: Dict[str, Any]) -> str:
        seq1 = result["aligned_seq1"]
        seq2 = result["aligned_seq2"]
        markers = result["marker_line"]
        lines: List[str] = []
        for start in range(0, len(seq1), 60):
            part1 = seq1[start : start + 60]
            part2 = seq2[start : start + 60]
            mark = markers[start : start + 60]
            colored1: List[str] = []
            colored2: List[str] = []
            for a, b in zip(part1, part2):
                if a == "-" or b == "-":
                    color = "#9AA4B2"
                elif a == b:
                    color = "#3CE58E"
                else:
                    color = "#FF6B6B"
                colored1.append(f"[color={color}]{a}[/color]")
                colored2.append(f"[color={color}]{b}[/color]")
            lines.append("".join(colored1))
            lines.append(mark)
            lines.append("".join(colored2))
            lines.append("")
        return "\n".join(lines)

    def _build_ai_explanation(
        self,
        query: str,
        disease_facts: Dict[str, Any],
        local_results: List[Dict[str, Any]],
        genes: List[Dict[str, Any]],
        disease_profile: Dict[str, Any],
    ) -> str:
        genetic_flag = disease_facts.get("is_genetic")
        if genetic_flag is True:
            inheritance_line = "This condition has a clear genetic or hereditary component."
        elif genetic_flag is False:
            inheritance_line = "This condition is not explained by genetics alone and may involve acquired or multifactorial causes."
        else:
            inheritance_line = "The genetic contribution is not yet classified in the local disease facts cache."

        medlineplus = cast(Dict[str, Any], disease_profile.get("medlineplus", {}))
        live_summary = str(medlineplus.get("summary", "")).strip()

        summary_line = ""
        if live_summary:
            summary_line = live_summary
        elif local_results:
            summary_line = local_results[0].get("description", "")
        elif genes:
            summary_line = genes[0].get("summary", "")
        else:
            summary_line = f"No detailed disease summary is cached yet for {query}."

        gene_line = ""
        if local_results:
            gene_line = f"Genes currently linked in the local database: {', '.join(local_results[0].get('genes', []))}."
        elif genes:
            gene_line = f"Top related NCBI gene result: {genes[0].get('symbol', '-')}, Gene ID {genes[0].get('gene_id', '-')}."
        else:
            gene_line = "No strong gene association was identified in the current result set."

        clinical_sections = cast(Dict[str, Any], disease_profile.get("clinical_sections", {}))
        symptom_preview = cast(List[str], clinical_sections.get("symptoms", disease_facts.get("symptoms", [])))
        symptom_line = ""
        if symptom_preview:
            symptom_line = "Key symptoms include " + ", ".join(symptom_preview[:3]) + "."
        else:
            symptom_line = "Symptom details are not yet cached locally."

        treatment_preview = cast(List[str], clinical_sections.get("treatment", disease_facts.get("treatment", [])))
        treatment_line = ""
        if treatment_preview:
            treatment_line = treatment_preview[0]
        else:
            treatment_line = "Treatment details are not yet cached locally."

        source_note = ""
        if medlineplus.get("url"):
            source_note = f"Patient-facing summary source: {medlineplus.get('source', 'MedlinePlus')}."
        elif disease_profile.get("medgen_ids"):
            source_note = "The profile is mapped to MedGen concepts and enriched with cached local notes."
        else:
            source_note = "The profile currently relies on local notes and NCBI-linked results."

        return (
            f"Simple explanation for {query}:\n\n"
            f"{summary_line}\n\n"
            f"{inheritance_line}\n\n"
            f"{gene_line}\n\n"
            f"{symptom_line}\n\n"
            f"Care or treatment note: {treatment_line}\n\n"
            f"{source_note}\n\n"
            "This panel is currently an AI-style explanation built from cached disease facts and live official-source enrichment, not a full generative medical model."
        )

    def clear_search_action(self) -> None:
        self.root.ids.search_input.text = ""
        self.root.ids.local_gene_title.text = "Disease / Gene Information"
        self.root.ids.local_gene_body.text = "Search to view local disease-gene information."
        self.root.ids.ncbi_gene_title.text = "NCBI Gene Summary"
        self.root.ids.ncbi_gene_body.text = "Search to view live NCBI gene summaries."
        self.root.ids.related_diseases.text = "-"
        self.root.ids.protein_info.text = "-"
        self.root.ids.external_links.text = "-"
        self.root.ids.disease_type_label.text = "Disease Type: Search a disease to load detailed local clinical notes"
        self.root.ids.symptoms_body.text = "Search a disease to view detailed symptoms."
        self.root.ids.precautions_body.text = "Search a disease to view precautions."
        self.root.ids.treatment_body.text = "Search a disease to view treatment or care details."
        self.root.ids.ai_explanation_body.text = "Search a disease to generate a simple explanation panel."
        self.root.ids.status_label.text = "Search panel cleared."

    def _set_status(self, text: str) -> None:
        self.root.ids.status_label.text = text


if __name__ == "__main__":
    BioExplorerApp().run()

#bullshit09999999#
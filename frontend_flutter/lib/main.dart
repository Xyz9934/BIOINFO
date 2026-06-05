import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

void main() {
  runApp(const BioinformaticsApp());
}

class BioinformaticsApp extends StatelessWidget {
  const BioinformaticsApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'Bioinformatics Explorer',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF0E7490),
          brightness: Brightness.light,
        ).copyWith(
          secondary: const Color(0xFF22C55E),
        ),
        scaffoldBackgroundColor: const Color(0xFFF4FBFD),
        useMaterial3: true,
      ),
      home: const HomePage(),
    );
  }
}

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  final TextEditingController _sequenceController = TextEditingController();
  final TextEditingController _diseaseController = TextEditingController();
  final TextEditingController _apiUrlController = TextEditingController(
    text: 'http://10.0.2.2:8000',
  );

  Map<String, dynamic>? _sequenceResult;
  List<dynamic> _diseaseResults = <dynamic>[];
  List<dynamic> _ncbiGeneResults = <dynamic>[];
  String? _sequenceError;
  String? _diseaseError;
  bool _analyzing = false;
  bool _searching = false;

  @override
  void dispose() {
    _sequenceController.dispose();
    _diseaseController.dispose();
    _apiUrlController.dispose();
    super.dispose();
  }

  String get _baseUrl => _apiUrlController.text.trim();

  Future<void> _analyzeSequence() async {
    setState(() {
      _analyzing = true;
      _sequenceError = null;
    });

    try {
      final response = await http.post(
        Uri.parse('$_baseUrl/analyze'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'sequence': _sequenceController.text}),
      );

      final body = jsonDecode(response.body) as Map<String, dynamic>;

      if (response.statusCode >= 400) {
        setState(() {
          _sequenceError = body['detail']?.toString() ?? 'Sequence analysis failed.';
          _sequenceResult = null;
        });
      } else {
        setState(() {
          _sequenceResult = body;
        });
      }
    } catch (_) {
      setState(() {
        _sequenceError = 'Could not connect to the Python backend at $_baseUrl.';
        _sequenceResult = null;
      });
    } finally {
      setState(() {
        _analyzing = false;
      });
    }
  }

  Future<void> _searchDisease() async {
    setState(() {
      _searching = true;
      _diseaseError = null;
      _ncbiGeneResults = <dynamic>[];
    });

    try {
      final localResponse = await http.post(
        Uri.parse('$_baseUrl/diseases/search'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'query': _diseaseController.text}),
      );

      final ncbiResponse = await http.post(
        Uri.parse('$_baseUrl/genes/search'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'query': _diseaseController.text}),
      );

      final localBody = jsonDecode(localResponse.body) as Map<String, dynamic>;
      final ncbiBody = jsonDecode(ncbiResponse.body) as Map<String, dynamic>;

      if (localResponse.statusCode >= 400 && ncbiResponse.statusCode >= 400) {
        setState(() {
          _diseaseError = ncbiBody['detail']?.toString() ??
              localBody['detail']?.toString() ??
              'Disease search failed.';
          _diseaseResults = <dynamic>[];
          _ncbiGeneResults = <dynamic>[];
        });
      } else {
        setState(() {
          _diseaseResults = (localBody['results'] as List<dynamic>? ?? <dynamic>[]);
          _ncbiGeneResults = (ncbiBody['results'] as List<dynamic>? ?? <dynamic>[]);
          if (localResponse.statusCode >= 400 && _ncbiGeneResults.isNotEmpty) {
            _diseaseError = null;
          } else if (ncbiResponse.statusCode >= 400 && _diseaseResults.isNotEmpty) {
            _diseaseError = null;
          } else if (ncbiResponse.statusCode >= 400) {
            _diseaseError = ncbiBody['detail']?.toString();
          }
        });
      }
    } catch (_) {
      setState(() {
        _diseaseError = 'Could not connect to the Python backend at $_baseUrl.';
        _diseaseResults = <dynamic>[];
        _ncbiGeneResults = <dynamic>[];
      });
    } finally {
      setState(() {
        _searching = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: LayoutBuilder(
          builder: (context, constraints) {
            final isWide = constraints.maxWidth > 900;

            return SingleChildScrollView(
              padding: const EdgeInsets.all(24),
              child: Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 1200),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _HeroBanner(isWide: isWide),
                      const SizedBox(height: 24),
                      _ToolCard(
                        title: 'Backend Connection',
                        subtitle: 'For Android emulator, keep 10.0.2.2. For a real phone APK, replace this with your deployed Python API URL.',
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            TextField(
                              controller: _apiUrlController,
                              decoration: const InputDecoration(
                                labelText: 'Python API Base URL',
                                hintText: 'Example: https://your-api-domain.com',
                                border: OutlineInputBorder(),
                              ),
                            ),
                            const SizedBox(height: 10),
                            const Text(
                              'Examples: Android emulator = http://10.0.2.2:8000, same PC testing = http://127.0.0.1:8000, real hosted backend = https://your-domain.com',
                              style: TextStyle(color: Color(0xFF475569)),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 24),
                      Wrap(
                        spacing: 24,
                        runSpacing: 24,
                        children: [
                          SizedBox(
                            width: isWide ? 560 : constraints.maxWidth,
                            child: _ToolCard(
                              title: 'DNA Sequence Analyzer',
                              subtitle: 'Paste a raw DNA sequence or FASTA input to calculate GC content, nucleotide counts, reverse complement, RNA, and protein.',
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  TextField(
                                    controller: _sequenceController,
                                    minLines: 4,
                                    maxLines: 8,
                                    decoration: const InputDecoration(
                                      labelText: 'DNA or FASTA Sequence',
                                      hintText: '>sample_1\nATGGCCATTGTAATGGGCCGCTGAAAGGGTGCCCGATAG',
                                      border: OutlineInputBorder(),
                                    ),
                                  ),
                                  const SizedBox(height: 10),
                                  const Text(
                                    'Allowed bases: A, T, G, C. FASTA headers starting with > are supported.',
                                    style: TextStyle(color: Color(0xFF475569)),
                                  ),
                                  const SizedBox(height: 16),
                                  FilledButton(
                                    onPressed: _analyzing ? null : _analyzeSequence,
                                    child: Text(_analyzing ? 'Analyzing...' : 'Analyze Sequence'),
                                  ),
                                  if (_sequenceError != null) ...[
                                    const SizedBox(height: 16),
                                    Text(
                                      _sequenceError!,
                                      style: const TextStyle(color: Colors.red),
                                    ),
                                  ],
                                  if (_sequenceResult != null) ...[
                                    const SizedBox(height: 20),
                                    if (_sequenceResult!['fasta_header'] != null)
                                      _ResultTile(
                                        label: 'FASTA Header',
                                        value: _sequenceResult!['fasta_header'].toString(),
                                      ),
                                    _ResultTile(label: 'Length', value: '${_sequenceResult!['length']} bp'),
                                    _ResultTile(label: 'GC Content', value: '${_sequenceResult!['gc_content']}%'),
                                    _ResultTile(
                                      label: 'Nucleotide Counts',
                                      value: _formatNucleotideCounts(
                                        _sequenceResult!['nucleotide_counts'] as Map<String, dynamic>? ??
                                            <String, dynamic>{},
                                      ),
                                    ),
                                    _ResultTile(
                                      label: 'Reverse Complement',
                                      value: _sequenceResult!['reverse_complement'].toString(),
                                    ),
                                    _ResultTile(
                                      label: 'RNA Transcript',
                                      value: _sequenceResult!['rna_transcript'].toString(),
                                    ),
                                    _ResultTile(label: 'Protein', value: _sequenceResult!['protein'].toString()),
                                    _ResultTile(
                                      label: 'Codons Used',
                                      value:
                                          '${_sequenceResult!['complete_codons']} complete codons, ${_sequenceResult!['incomplete_codon_bases']} leftover base(s)',
                                    ),
                                    if (_sequenceResult!['warning'] != null)
                                      _ResultTile(
                                        label: 'Note',
                                        value: _sequenceResult!['warning'].toString(),
                                      ),
                                  ],
                                ],
                              ),
                            ),
                          ),
                          SizedBox(
                            width: isWide ? 560 : constraints.maxWidth,
                            child: _ToolCard(
                              title: 'Disease to Gene Search',
                              subtitle: 'Search by disease name or gene name and view the linked disease records using a starter dataset designed for later API upgrades.',
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  TextField(
                                    controller: _diseaseController,
                                    decoration: const InputDecoration(
                                      labelText: 'Disease or Gene Name',
                                      hintText: 'Example: Breast cancer or BRCA1',
                                      border: OutlineInputBorder(),
                                    ),
                                  ),
                                  const SizedBox(height: 16),
                                  FilledButton(
                                    onPressed: _searching ? null : _searchDisease,
                                    child: Text(_searching ? 'Searching...' : 'Search Disease'),
                                  ),
                                  if (_diseaseError != null) ...[
                                    const SizedBox(height: 16),
                                    Text(
                                      _diseaseError!,
                                      style: const TextStyle(color: Colors.red),
                                    ),
                                  ],
                                  const SizedBox(height: 20),
                                  if (_diseaseResults.isEmpty && _ncbiGeneResults.isEmpty && !_searching)
                                    const Text('No search results yet. Try Breast Cancer, Parkinson, Cystic Fibrosis, BRCA1, or HBB.'),
                                  if (_diseaseResults.isNotEmpty) ...[
                                    Text(
                                      'Local disease-gene matches',
                                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                            fontWeight: FontWeight.bold,
                                          ),
                                    ),
                                    const SizedBox(height: 12),
                                  ],
                                  ..._diseaseResults.map(
                                    (item) => Card(
                                      margin: const EdgeInsets.only(bottom: 12),
                                      child: Padding(
                                        padding: const EdgeInsets.all(16),
                                        child: Column(
                                          crossAxisAlignment: CrossAxisAlignment.start,
                                          children: [
                                            Text(
                                              item['disease'].toString(),
                                              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                                    fontWeight: FontWeight.bold,
                                                  ),
                                            ),
                                            const SizedBox(height: 8),
                                            Text(item['description'].toString()),
                                            const SizedBox(height: 12),
                                            Wrap(
                                              spacing: 8,
                                              runSpacing: 8,
                                              children: (item['matched_by'] as List<dynamic>? ?? <dynamic>[])
                                                  .map(
                                                    (match) => Chip(
                                                      label: Text('Matched by: ${match.toString()}'),
                                                    ),
                                                  )
                                                  .toList(),
                                            ),
                                            const SizedBox(height: 12),
                                            Wrap(
                                              spacing: 8,
                                              runSpacing: 8,
                                              children: (item['genes'] as List<dynamic>)
                                                  .map(
                                                    (gene) => Chip(
                                                      label: Text(gene.toString()),
                                                      backgroundColor: const Color(0xFFD9F99D),
                                                    ),
                                                  )
                                                  .toList(),
                                            ),
                                          ],
                                        ),
                                      ),
                                    ),
                                  ),
                                  if (_ncbiGeneResults.isNotEmpty) ...[
                                    const SizedBox(height: 16),
                                    Text(
                                      'NCBI Gene matches',
                                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                            fontWeight: FontWeight.bold,
                                          ),
                                    ),
                                    const SizedBox(height: 12),
                                  ],
                                  ..._ncbiGeneResults.map(
                                    (item) => Card(
                                      margin: const EdgeInsets.only(bottom: 12),
                                      color: const Color(0xFFF0FDF4),
                                      child: Padding(
                                        padding: const EdgeInsets.all(16),
                                        child: Column(
                                          crossAxisAlignment: CrossAxisAlignment.start,
                                          children: [
                                            Text(
                                              '${item['symbol']} (${item['gene_id']})',
                                              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                                    fontWeight: FontWeight.bold,
                                                  ),
                                            ),
                                            const SizedBox(height: 8),
                                            Text(item['official_name']?.toString() ?? ''),
                                            if ((item['organism']?.toString() ?? '').isNotEmpty) ...[
                                              const SizedBox(height: 8),
                                              Text('Organism: ${item['organism']}'),
                                            ],
                                            if ((item['chromosome']?.toString() ?? '').isNotEmpty)
                                              Text('Chromosome: ${item['chromosome']}'),
                                            if ((item['map_location']?.toString() ?? '').isNotEmpty)
                                              Text('Map location: ${item['map_location']}'),
                                            if ((item['summary']?.toString() ?? '').isNotEmpty) ...[
                                              const SizedBox(height: 10),
                                              Text(item['summary'].toString()),
                                            ],
                                            const SizedBox(height: 10),
                                            SelectableText(item['ncbi_url'].toString()),
                                          ],
                                        ),
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            );
          },
        ),
      ),
    );
  }

  String _formatNucleotideCounts(Map<String, dynamic> counts) {
    const order = ['A', 'T', 'G', 'C'];
    return order.map((base) => '$base: ${counts[base] ?? 0}').join(' | ');
  }
}

class _HeroBanner extends StatelessWidget {
  const _HeroBanner({required this.isWide});

  final bool isWide;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(28),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(28),
        gradient: const LinearGradient(
          colors: [Color(0xFF083344), Color(0xFF155E75), Color(0xFF0F766E)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
      ),
      child: isWide
          ? Row(
              children: [
                Expanded(child: _BannerText()),
                const SizedBox(width: 24),
                const _DnaBadge(),
              ],
            )
          : const Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _BannerText(),
                SizedBox(height: 20),
                _DnaBadge(),
              ],
            ),
    );
  }
}

class _BannerText extends StatelessWidget {
  const _BannerText();

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
          decoration: BoxDecoration(
            color: Colors.white.withValues(alpha: 0.14),
            borderRadius: BorderRadius.circular(999),
          ),
          child: const Text(
            'Biotechnology + Bioinformatics Student Project',
            style: TextStyle(color: Colors.white),
          ),
        ),
        const SizedBox(height: 16),
        Text(
          'Bioinformatics Explorer',
          style: Theme.of(context).textTheme.displaySmall?.copyWith(
                color: Colors.white,
                fontWeight: FontWeight.bold,
              ),
        ),
        const SizedBox(height: 12),
        const Text(
          'One app for sequence analysis and disease-gene discovery, designed so you can later connect NCBI or AI features without changing the whole structure.',
          style: TextStyle(color: Color(0xFFE6FFFB), height: 1.5),
        ),
      ],
    );
  }
}

class _DnaBadge extends StatelessWidget {
  const _DnaBadge();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 220,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: Colors.white24),
      ),
      child: const Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Live Features', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
          SizedBox(height: 12),
          Text('GC Content', style: TextStyle(color: Colors.white70)),
          Text('FASTA Support', style: TextStyle(color: Colors.white70)),
          Text('Nucleotide Counts', style: TextStyle(color: Colors.white70)),
          Text('Reverse Complement', style: TextStyle(color: Colors.white70)),
          Text('Protein Translation', style: TextStyle(color: Colors.white70)),
          Text('Disease and Gene Search', style: TextStyle(color: Colors.white70)),
        ],
      ),
    );
  }
}

class _ToolCard extends StatelessWidget {
  const _ToolCard({
    required this.title,
    required this.subtitle,
    required this.child,
  });

  final String title;
  final String subtitle;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(24),
        boxShadow: const [
          BoxShadow(
            color: Color(0x120F172A),
            blurRadius: 24,
            offset: Offset(0, 12),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          Text(subtitle, style: const TextStyle(color: Color(0xFF475569), height: 1.45)),
          const SizedBox(height: 20),
          child,
        ],
      ),
    );
  }
}

class _ResultTile extends StatelessWidget {
  const _ResultTile({
    required this.label,
    required this.value,
  });

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFFF8FAFC),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: const TextStyle(fontWeight: FontWeight.w600, color: Color(0xFF0F172A)),
          ),
          const SizedBox(height: 6),
          SelectableText(value),
        ],
      ),
    );
  }
}

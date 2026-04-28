import 'package:flutter/material.dart';
import 'package:fortress_mobile/core/app_theme.dart';

class AIReportViewer extends StatelessWidget {
  final Map<String, dynamic> reportData;

  const AIReportViewer({super.key, required this.reportData});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF4F7F9),
      appBar: AppBar(
        title: const Text('AI MISSION REPORT', style: TextStyle(fontWeight: FontWeight.w900, fontSize: 16)),
        backgroundColor: Colors.white,
        foregroundColor: AppTheme.navySecondary,
        elevation: 0,
        actions: [
          IconButton(onPressed: () {}, icon: const Icon(Icons.download_outlined)),
          IconButton(onPressed: () {}, icon: const Icon(Icons.share_outlined)),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          children: [
            _buildStatusHeader(),
            const SizedBox(height: 20),
            _buildSection('MISSION SUMMARY', [
                _buildRow('Report ID', reportData['report_id'] ?? 'N/A'),
                _buildRow('Type', reportData['mission_type'] ?? 'N/A'),
                _buildRow('Date', reportData['timestamp']?.split('T')[0] ?? 'N/A'),
            ]),
            const SizedBox(height: 20),
            _buildSection('ORIGINAL REQUEST', [
                Text(
                  reportData['original_request']?['message'] ?? 'No message provided.',
                  style: TextStyle(color: Colors.grey[800], height: 1.5),
                ),
            ]),
            const SizedBox(height: 20),
            _buildSection('FULFILLMENT LOG', [
                ...(reportData['fulfillment_summary']?['logs'] as List? ?? []).map((log) => _buildFulfillmentTile(log)),
            ]),
            const SizedBox(height: 40),
            _buildAISeal(),
          ],
        ),
      ),
    );
  }

  Widget _buildStatusHeader() {
    final bool isSuccess = reportData['status'] == 'SUCCESSFUL';
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: isSuccess 
            ? [AppTheme.tealPrimary, const Color(0xFF00897B)] 
            : [const Color(0xFF546E7A), const Color(0xFF37474F)],
        ),
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: (isSuccess ? AppTheme.tealPrimary : Colors.grey).withOpacity(0.3),
            blurRadius: 20,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: Column(
        children: [
          Icon(
            isSuccess ? Icons.check_circle_outline : Icons.pending_actions,
            color: Colors.white,
            size: 48,
          ),
          const SizedBox(height: 12),
          Text(
            isSuccess ? 'MISSION COMPLETE' : 'PARTIAL FULFILLMENT',
            style: const TextStyle(
              color: Colors.white,
              fontWeight: FontWeight.w900,
              fontSize: 20,
              letterSpacing: 1,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            isSuccess ? 'All units delivered successfully' : 'Mission remains active for pending units',
            style: TextStyle(color: Colors.white.withOpacity(0.8), fontSize: 13),
          ),
        ],
      ),
    );
  }

  Widget _buildSection(String title, List<Widget> children) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.grey.withOpacity(0.1)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: const TextStyle(
              fontWeight: FontWeight.w900,
              fontSize: 12,
              color: AppTheme.tealPrimary,
              letterSpacing: 1.2,
            ),
          ),
          const SizedBox(height: 16),
          ...children,
        ],
      ),
    );
  }

  Widget _buildRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8.0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: TextStyle(color: Colors.grey[600], fontSize: 14)),
          Text(value, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14)),
        ],
      ),
    );
  }

  Widget _buildFulfillmentTile(dynamic log) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFFF8F9FB),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Row(
        children: [
          const Icon(Icons.business_outlined, color: AppTheme.navySecondary, size: 20),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  log['supplier_ngo_name'] ?? 'NGO Supplier',
                  style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 14),
                ),
                Text(
                  'Committed ${log['committed_qty']} units',
                  style: TextStyle(color: Colors.grey[600], fontSize: 12),
                ),
              ],
            ),
          ),
          const Icon(Icons.chevron_right, color: Colors.grey),
        ],
      ),
    );
  }

  Widget _buildAISeal() {
    return Column(
      children: [
        Opacity(
          opacity: 0.2,
          child: Image.network(
            'https://upload.wikimedia.org/wikipedia/commons/thumb/c/c1/Google_Gemini_logo.svg/2560px-Google_Gemini_logo.svg.png',
            height: 40,
          ),
        ),
        const SizedBox(height: 8),
        const Text(
          'GENERATED BY FORTRESS AI ENGINE',
          style: TextStyle(
            fontSize: 10,
            fontWeight: FontWeight.w900,
            color: Colors.grey,
            letterSpacing: 2,
          ),
        ),
      ],
    );
  }
}

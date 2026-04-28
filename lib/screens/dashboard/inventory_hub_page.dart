import 'package:flutter/material.dart';
import 'package:fortress_mobile/core/app_theme.dart';

class InventoryHubPage extends StatefulWidget {
  final String role;

  const InventoryHubPage({super.key, required this.role});

  @override
  State<InventoryHubPage> createState() => _InventoryHubPageState();
}

class _InventoryHubPageState extends State<InventoryHubPage> {
  // Mock Data Ledger
  final List<Map<String, String>> _files = [
    {'name': 'Disaster_Report_Taluka_A.pdf', 'date': '2026-04-28 10:30', 'status': 'Ready'},
    {'name': 'Oxygen_Cylinder_Inventory.xlsx', 'date': '2026-04-28 09:15', 'status': 'Ready'},
    {'name': 'Volunteer_List_Phase_1.pdf', 'date': '2026-04-27 18:45', 'status': 'Ready'},
  ];

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        if (widget.role != 'NGO_MEMBER') _buildActionHeader(),
        Expanded(
          child: ListView.separated(
            padding: const EdgeInsets.all(24.0),
            itemCount: _files.length,
            separatorBuilder: (context, index) => const SizedBox(height: 16),
            itemBuilder: (context, index) {
              final file = _files[index];
              return _buildFileCard(file);
            },
          ),
        ),
      ],
    );
  }

  Widget _buildActionHeader() {
    return Container(
      padding: const EdgeInsets.fromLTRB(24, 8, 24, 32),
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.only(
          bottomLeft: Radius.circular(32),
          bottomRight: Radius.circular(32),
        ),
        boxShadow: [
          BoxShadow(color: Colors.black12, blurRadius: 30, offset: Offset(0, 10)),
        ],
      ),
      child: Row(
        children: [
          Expanded(
            child: _actionButton(
              'Upload Data',
              Icons.add_to_photos_rounded,
              AppTheme.navySecondary.withOpacity(0.05),
              AppTheme.navySecondary,
              () => _showUploadSimulation(),
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: _actionButton(
              'Manage AI',
              Icons.auto_awesome_rounded,
              AppTheme.tealPrimary.withOpacity(0.1),
              AppTheme.tealPrimary,
              () => _showManageSimulation(),
            ),
          ),
        ],
      ),
    );
  }

  Widget _actionButton(String label, IconData icon, Color bg, Color text, VoidCallback onTap) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 20),
        decoration: BoxDecoration(
          color: bg,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: text.withOpacity(0.05)),
        ),
        child: Column(
          children: [
            Icon(icon, color: text, size: 30),
            const SizedBox(height: 10),
            Text(label, style: TextStyle(color: text, fontWeight: FontWeight.w900, fontSize: 12, letterSpacing: 0.5)),
          ],
        ),
      ),
    );
  }

  Widget _buildFileCard(Map<String, String> file) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: Colors.grey.shade100),
        boxShadow: [
          BoxShadow(color: Colors.black.withOpacity(0.02), blurRadius: 15, offset: const Offset(0, 8)),
        ],
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: AppTheme.backgroundGray,
              borderRadius: BorderRadius.circular(16),
            ),
            child: const Icon(Icons.article_rounded, color: AppTheme.navySecondary, size: 22),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  file['name']!,
                  style: const TextStyle(fontWeight: FontWeight.w900, color: AppTheme.navySecondary, fontSize: 14),
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 4),
                Text(
                  file['date']!,
                  style: TextStyle(color: AppTheme.navySecondary.withOpacity(0.4), fontSize: 10, fontWeight: FontWeight.bold),
                ),
              ],
            ),
          ),
          Container(
            decoration: BoxDecoration(
              color: AppTheme.tealPrimary.withOpacity(0.1),
              borderRadius: BorderRadius.circular(12),
            ),
            child: IconButton(
              icon: const Icon(Icons.arrow_forward_rounded, color: AppTheme.tealPrimary, size: 20),
              onPressed: () {},
            ),
          ),
        ],
      ),
    );
  }

  void _showUploadSimulation() {
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(30))),
      builder: (context) => Padding(
        padding: const EdgeInsets.all(32.0),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.cloud_upload_outlined, size: 64, color: AppTheme.navySecondary),
            const SizedBox(height: 16),
            const Text('Upload New Inventory', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            const Text('Select a .csv or .pdf file to ingest into the NGO ledger.'),
            const SizedBox(height: 24),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: () => Navigator.pop(context),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.navySecondary,
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
                child: const Text('SELECT FILE', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _showManageSimulation() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: const Row(
          children: [
            Icon(Icons.psychology_rounded, color: AppTheme.tealPrimary),
            SizedBox(width: 12),
            Text('Omni-Manage AI'),
          ],
        ),
        content: const Text(
          'This will trigger the AI to scrape all raw inventory data and generate a "Paper-Readable" printable report. Proceed?',
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('CANCEL')),
          ElevatedButton(
            onPressed: () => Navigator.pop(context),
            style: ElevatedButton.styleFrom(backgroundColor: AppTheme.tealPrimary),
            child: const Text('RUN SCRAPER', style: TextStyle(color: Colors.white)),
          ),
        ],
      ),
    );
  }
}

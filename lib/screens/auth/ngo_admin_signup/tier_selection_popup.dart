import 'package:flutter/material.dart';
import 'package:fortress_mobile/core/app_theme.dart';
import 'package:fortress_mobile/screens/auth/ngo_admin_signup/org_details_screen.dart';

class TierSelectionPopup extends StatelessWidget {
  const TierSelectionPopup({super.key});

  @override
  Widget build(BuildContext context) {
    return Dialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppTheme.borderRadius)),
      child: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text(
                  'Select NGO Tier',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppTheme.navySecondary),
                ),
                IconButton(
                  icon: const Icon(Icons.close_rounded, color: Colors.grey),
                  onPressed: () => Navigator.of(context).pop(),
                ),
              ],
            ),
            const SizedBox(height: 24),
            _buildTierCard(
              context,
              'Tier 1 NGO',
              'Standard relief operations. No audit required.',
              Icons.looks_one_rounded,
            ),
            const SizedBox(height: 16),
            _buildTierCard(
              context,
              'Tier 2 NGO',
              'High-capacity operations. Requires document audit.',
              Icons.looks_two_rounded,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTierCard(BuildContext context, String title, String desc, IconData icon) {
    return InkWell(
      onTap: () {
        Navigator.of(context).pop(); // Close popup
        Navigator.of(context).push(
          MaterialPageRoute(builder: (context) => const OrgDetailsScreen()),
        );
      },
      borderRadius: BorderRadius.circular(AppTheme.borderRadius),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(AppTheme.borderRadius),
          border: Border.all(color: Colors.grey.withOpacity(0.2)),
        ),
        child: Row(
          children: [
            Icon(icon, color: AppTheme.tealPrimary, size: 32),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: const TextStyle(fontWeight: FontWeight.bold)),
                  Text(desc, style: const TextStyle(fontSize: 12, color: Colors.grey)),
                ],
              ),
            ),
            const Icon(Icons.arrow_forward_ios_rounded, size: 16, color: Colors.grey),
          ],
        ),
      ),
    );
  }
}

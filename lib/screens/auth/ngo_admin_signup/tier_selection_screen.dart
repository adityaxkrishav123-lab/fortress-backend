import 'package:flutter/material.dart';
import 'package:fortress_mobile/core/app_theme.dart';
import 'package:fortress_mobile/screens/auth/ngo_admin_signup/org_details_screen.dart';

class TierSelectionScreen extends StatefulWidget {
  const TierSelectionScreen({super.key});

  @override
  State<TierSelectionScreen> createState() => _TierSelectionScreenState();
}

class _TierSelectionScreenState extends State<TierSelectionScreen> {
  int? _selectedTier;

  void _showInfoPopup(String tier, String info) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppTheme.borderRadius)),
        title: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text('About $tier', style: const TextStyle(color: AppTheme.navySecondary, fontSize: 18)),
            IconButton(
              icon: const Icon(Icons.cancel_rounded, color: Colors.grey),
              onPressed: () => Navigator.of(context).pop(),
            ),
          ],
        ),
        content: Text(info, style: const TextStyle(color: Colors.black87)),
      ),
    );
  }

  void _onNext() {
    if (_selectedTier == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please select a Tier'), backgroundColor: Colors.orange),
      );
      return;
    }
    Navigator.of(context).push(
      MaterialPageRoute(builder: (context) => OrgDetailsScreen(tier: _selectedTier!)),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Select NGO Tire'),
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new_rounded, color: AppTheme.navySecondary),
          onPressed: () => Navigator.of(context).pop(),
        ),
      ),
      body: Column(
        children: [
          Expanded(
            child: Padding(
              padding: const EdgeInsets.all(24.0),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  _buildTierCard(
                    'Tire 1 NGO',
                    'Standard relief operations. Requires Aadhar, PAN, and NGO Registration Certificate.',
                    1,
                  ),
                  const SizedBox(height: 24),
                  _buildTierCard(
                    'Tire 2 NGO',
                    'High-capacity operations. Requires Aadhar, PAN, NGO Registration, and COMPULSORY 12A Certificate.',
                    2,
                  ),
                  const SizedBox(height: 60),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      TextButton(
                        onPressed: () => Navigator.of(context).pop(),
                        child: const Text('Previous', style: TextStyle(color: Colors.grey)),
                      ),
                      ElevatedButton(
                        style: ElevatedButton.styleFrom(
                          minimumSize: const Size(120, 50),
                          backgroundColor: _selectedTier == null ? Colors.grey[300] : AppTheme.tealPrimary,
                        ),
                        onPressed: _selectedTier == null ? null : _onNext,
                        child: Text(
                          'Next',
                          style: TextStyle(color: _selectedTier == null ? Colors.grey[600] : Colors.white),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
          _buildProgressDots(1),
        ],
      ),
    );
  }

  Widget _buildTierCard(String title, String infoText, int tier) {
    bool isSelected = _selectedTier == tier;
    return InkWell(
      onTap: () => setState(() => _selectedTier = tier),
      borderRadius: BorderRadius.circular(AppTheme.borderRadius),
      child: Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(AppTheme.borderRadius),
          border: Border.all(
            color: isSelected ? AppTheme.tealPrimary : Colors.grey.withOpacity(0.2),
            width: isSelected ? 2 : 1,
          ),
          color: Colors.white,
          boxShadow: isSelected ? [BoxShadow(color: AppTheme.tealPrimary.withOpacity(0.1), blurRadius: 10)] : null,
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(title, style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: isSelected ? AppTheme.tealPrimary : AppTheme.navySecondary)),
            IconButton(
              icon: const Icon(Icons.info_outline_rounded, color: AppTheme.tealPrimary),
              onPressed: () => _showInfoPopup(title, infoText),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildProgressDots(int currentIndex) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 20.0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: List.generate(4, (index) {
          return Container(
            margin: const EdgeInsets.symmetric(horizontal: 4),
            width: 8,
            height: 8,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: index == currentIndex ? Colors.black : Colors.grey.shade400,
            ),
          );
        }),
      ),
    );
  }
}

import 'package:flutter/material.dart';
import 'package:fortress_mobile/core/app_theme.dart';

class RaiseRequestHubPage extends StatefulWidget {
  final String role;

  const RaiseRequestHubPage({super.key, required this.role});

  @override
  State<RaiseRequestHubPage> createState() => _RaiseRequestHubPageState();
}

class _RaiseRequestHubPageState extends State<RaiseRequestHubPage> {
  String? _selectedNgoHelpType;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(24.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Operational Dispatch',
            style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: AppTheme.navySecondary),
          ),
          const SizedBox(height: 8),
          Text(
            'Select the type of assistance required to scale your disaster response.',
            style: TextStyle(color: AppTheme.navySecondary.withOpacity(0.6), fontSize: 14),
          ),
          const SizedBox(height: 40),
          
          // NGO to NGO Section
          _buildHubCard(
            title: 'Request NGO Assistance',
            subtitle: 'Collaborate with nearby NGOs for commodities or specialized services.',
            icon: Icons.handshake_rounded,
            child: _buildNgoDropdown(),
          ),
          
          const SizedBox(height: 24),
          
          // NGO to Volunteer Section
          _buildHubCard(
            title: 'Recruit Volunteers',
            subtitle: 'Request manpower assistance from the local Taluka community.',
            icon: Icons.groups_rounded,
            child: SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: () => _showPopup('Volunteer'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.tealPrimary,
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
                child: const Text('RECRUIT NOW', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildHubCard({required String title, required String subtitle, required IconData icon, required Widget child}) {
    return Container(
      padding: const EdgeInsets.all(28),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(32),
        border: Border.all(color: Colors.grey.shade100),
        boxShadow: [
          BoxShadow(color: AppTheme.navySecondary.withOpacity(0.04), blurRadius: 30, offset: const Offset(0, 15)),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: AppTheme.tealPrimary.withOpacity(0.08),
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Icon(icon, color: AppTheme.tealPrimary, size: 28),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Text(
                  title,
                  style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w900, color: AppTheme.navySecondary),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            subtitle,
            style: TextStyle(color: AppTheme.navySecondary.withOpacity(0.4), fontSize: 13, height: 1.5, fontWeight: FontWeight.w500),
          ),
          const SizedBox(height: 28),
          child,
        ],
      ),
    );
  }

  Widget _buildNgoDropdown() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
          decoration: BoxDecoration(
            color: AppTheme.backgroundGray,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: Colors.grey.shade200),
          ),
          child: DropdownButtonHideUnderline(
            child: DropdownButton<String>(
              isExpanded: true,
              hint: const Text('Select Assistance Category', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
              value: _selectedNgoHelpType,
              icon: const Icon(Icons.keyboard_command_key_rounded, size: 18, color: AppTheme.navySecondary),
              items: [
                _buildDropdownItem('Instant Help', 'Commodities dispatch'),
                _buildDropdownItem('Service', 'Expertise & Manpower'),
              ],
              onChanged: (val) {
                setState(() => _selectedNgoHelpType = val);
                if (val != null) {
                  _showPopup(val);
                }
              },
            ),
          ),
        ),
      ],
    );
  }

  DropdownMenuItem<String> _buildDropdownItem(String label, String desc) {
    return DropdownMenuItem(
      value: label,
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(fontWeight: FontWeight.bold)),
          IconButton(
            icon: const Icon(Icons.info_outline_rounded, size: 18, color: AppTheme.tealPrimary),
            onPressed: () => _showInfo(label, desc),
          ),
        ],
      ),
    );
  }

  void _showPopup(String type) {
    if (type == 'Instant Help') {
      _showInstantHelpPopup();
    } else if (type == 'Service') {
      _showServicePopup();
    } else {
      _showVolunteerPopup();
    }
  }

  void _showInstantHelpPopup() {
    showDialog(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setPopupState) {
          int quantity = 1;
          String? selectedItem;
          return AlertDialog(
            backgroundColor: Colors.white,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(28)),
            title: Column(
              children: [
                Container(
                  width: 40,
                  height: 4,
                  decoration: BoxDecoration(color: Colors.grey.shade300, borderRadius: BorderRadius.circular(10)),
                ),
                const SizedBox(height: 20),
                const Text('Instant Dispatch', style: TextStyle(fontWeight: FontWeight.w900, color: AppTheme.navySecondary, fontSize: 22)),
              ],
            ),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Text('Choose the critical resource needed:', style: TextStyle(fontSize: 13, color: Colors.grey)),
                const SizedBox(height: 20),
                Wrap(
                  spacing: 10,
                  runSpacing: 10,
                  alignment: WrapAlignment.center,
                  children: ['Food', 'Oxygen', 'Water', 'Medicine', 'Shelter'].map((item) {
                    bool isSelected = selectedItem == item;
                    return GestureDetector(
                      onTap: () => setPopupState(() => selectedItem = item),
                      child: AnimatedContainer(
                        duration: const Duration(milliseconds: 300),
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                        decoration: BoxDecoration(
                          color: isSelected ? AppTheme.tealPrimary : Colors.white,
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: isSelected ? AppTheme.tealPrimary : Colors.grey.shade300, width: 1.5),
                          boxShadow: isSelected ? [BoxShadow(color: AppTheme.tealPrimary.withOpacity(0.3), blurRadius: 8, offset: const Offset(0, 4))] : [],
                        ),
                        child: Text(
                          item,
                          style: TextStyle(color: isSelected ? Colors.white : AppTheme.navySecondary, fontWeight: FontWeight.bold, fontSize: 13),
                        ),
                      ),
                    );
                  }).toList(),
                ),
                const SizedBox(height: 32),
                const Text('QUANTITY', style: TextStyle(fontSize: 10, fontWeight: FontWeight.w900, letterSpacing: 2, color: AppTheme.navySecondary)),
                const SizedBox(height: 12),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  decoration: BoxDecoration(color: AppTheme.backgroundGray, borderRadius: BorderRadius.circular(16)),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      GestureDetector(
                        onTap: () => setPopupState(() => quantity = (quantity > 1) ? quantity - 1 : 1),
                        child: Container(padding: const EdgeInsets.all(8), decoration: const BoxDecoration(color: Colors.white, shape: BoxShape.circle), child: const Icon(Icons.remove, size: 20, color: AppTheme.navySecondary)),
                      ),
                      SizedBox(width: 80, child: Center(child: Text('$quantity', style: const TextStyle(fontSize: 28, fontWeight: FontWeight.w900, color: AppTheme.navySecondary)))),
                      GestureDetector(
                        onTap: () => setPopupState(() => quantity++),
                        child: Container(padding: const EdgeInsets.all(8), decoration: const BoxDecoration(color: Colors.white, shape: BoxShape.circle), child: const Icon(Icons.add, size: 20, color: AppTheme.navySecondary)),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            actionsPadding: const EdgeInsets.fromLTRB(24, 0, 24, 24),
            actions: [
              Row(
                children: [
                  Expanded(child: TextButton(onPressed: () => Navigator.pop(context), child: const Text('CANCEL', style: TextStyle(color: Colors.grey, fontWeight: FontWeight.bold)))),
                  Expanded(
                    child: ElevatedButton(
                      onPressed: selectedItem == null ? null : () => Navigator.pop(context),
                      style: ElevatedButton.styleFrom(backgroundColor: AppTheme.tealPrimary, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)), padding: const EdgeInsets.symmetric(vertical: 14)),
                      child: const Text('DISPATCH', style: TextStyle(color: Colors.white, fontWeight: FontWeight.w900)),
                    ),
                  ),
                ],
              ),
            ],
          );
        },
      ),
    );
  }

  void _showServicePopup() {
    showDialog(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setPopupState) {
          String? selectedType;
          List<String> selectedTags = [];
          final tagsMap = {
            'Medical': ['Blood Bank', 'Ambulance', 'Surgery', 'Trauma'],
            'Logistics': ['Heavy Transport', 'Storage', 'Route Clearing'],
            'Search & Rescue': ['Divers', 'Canine Unit', 'Drone Team'],
          };

          return AlertDialog(
            backgroundColor: Colors.white,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(28)),
            title: const Text('Service Mobilization', style: TextStyle(fontWeight: FontWeight.w900, color: AppTheme.navySecondary, fontSize: 22)),
            content: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('ORGANIZATIONAL TYPE', style: TextStyle(fontSize: 10, fontWeight: FontWeight.w900, letterSpacing: 1.5, color: Colors.grey)),
                  const SizedBox(height: 12),
                  DropdownButtonFormField<String>(
                    decoration: InputDecoration(filled: true, fillColor: AppTheme.backgroundGray, contentPadding: const EdgeInsets.symmetric(horizontal: 16), border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none)),
                    items: tagsMap.keys.map((s) => DropdownMenuItem(value: s, child: Text(s, style: const TextStyle(fontSize: 14)))).toList(),
                    onChanged: (val) => setPopupState(() { selectedType = val; selectedTags.clear(); }),
                    hint: const Text('Select Service Category'),
                  ),
                  if (selectedType != null) ...[
                    const SizedBox(height: 24),
                    const Text('SUBTYPE SPECIALIZATIONS', style: TextStyle(fontSize: 10, fontWeight: FontWeight.w900, letterSpacing: 1.5, color: Colors.grey)),
                    const SizedBox(height: 12),
                    Wrap(
                      spacing: 8, runSpacing: 8,
                      children: tagsMap[selectedType!]!.map((tag) {
                        bool isSelected = selectedTags.contains(tag);
                        return FilterChip(
                          label: Text(tag, style: TextStyle(fontSize: 11, color: isSelected ? Colors.white : AppTheme.navySecondary)),
                          selected: isSelected,
                          onSelected: (val) => setPopupState(() => val ? selectedTags.add(tag) : selectedTags.remove(tag)),
                          selectedColor: AppTheme.tealPrimary, checkmarkColor: Colors.white, backgroundColor: AppTheme.backgroundGray,
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                        );
                      }).toList(),
                    ),
                  ],
                  const SizedBox(height: 24),
                  const Text('MISSION MESSAGE', style: TextStyle(fontSize: 10, fontWeight: FontWeight.w900, letterSpacing: 1.5, color: Colors.grey)),
                  const SizedBox(height: 12),
                  TextField(
                    maxLines: 3,
                    decoration: InputDecoration(hintText: 'Describe the emergency scope...', hintStyle: const TextStyle(fontSize: 13), filled: true, fillColor: AppTheme.backgroundGray, border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none)),
                  ),
                ],
              ),
            ),
            actions: [
              TextButton(onPressed: () => Navigator.pop(context), child: const Text('CANCEL', style: TextStyle(color: Colors.grey))),
              ElevatedButton(
                onPressed: selectedType == null ? null : () => Navigator.pop(context),
                style: ElevatedButton.styleFrom(backgroundColor: AppTheme.tealPrimary, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))),
                child: const Text('GO', style: TextStyle(color: Colors.white, fontWeight: FontWeight.w900)),
              ),
            ],
          );
        },
      ),
    );
  }

  void _showVolunteerPopup() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: Colors.white,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(28)),
        title: const Text('Volunteer Call', style: TextStyle(fontWeight: FontWeight.w900, color: AppTheme.navySecondary, fontSize: 22)),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('PROFESSIONAL SKILLS REQUIRED', style: TextStyle(fontSize: 10, fontWeight: FontWeight.w900, letterSpacing: 1.5, color: Colors.grey)),
              const SizedBox(height: 12),
              Wrap(
                spacing: 8,
                children: ['Driver', 'Medic', 'General', 'Security'].map((p) => ChoiceChip(
                  label: Text(p, style: const TextStyle(fontSize: 12)),
                  selected: false,
                  backgroundColor: AppTheme.backgroundGray,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                )).toList(),
              ),
              const SizedBox(height: 24),
              const Text('MANPOWER COUNT', style: TextStyle(fontSize: 10, fontWeight: FontWeight.w900, letterSpacing: 1.5, color: Colors.grey)),
              const SizedBox(height: 12),
              TextField(
                decoration: InputDecoration(hintText: 'E.g. 50', prefixIcon: const Icon(Icons.people_outline, size: 20), filled: true, fillColor: AppTheme.backgroundGray, border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none)),
                keyboardType: TextInputType.number,
              ),
              const SizedBox(height: 24),
              const Text('STRATEGIC INSTRUCTIONS', style: TextStyle(fontSize: 10, fontWeight: FontWeight.w900, letterSpacing: 1.5, color: Colors.grey)),
              const SizedBox(height: 12),
              TextField(
                maxLines: 3,
                decoration: InputDecoration(hintText: 'Where and when to report...', hintStyle: const TextStyle(fontSize: 13), filled: true, fillColor: AppTheme.backgroundGray, border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none)),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('CANCEL', style: TextStyle(color: Colors.grey))),
          ElevatedButton(
            onPressed: () => Navigator.pop(context),
            style: ElevatedButton.styleFrom(backgroundColor: AppTheme.tealPrimary, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))),
            child: const Text('SUBMIT', style: TextStyle(color: Colors.white, fontWeight: FontWeight.w900)),
          ),
        ],
      ),
    );
  }

  void _showInfo(String title, String desc) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(title, style: const TextStyle(fontWeight: FontWeight.bold)),
        content: Text(desc),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('OK')),
        ],
      ),
    );
  }
}

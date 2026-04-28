import 'package:flutter/material.dart';
import 'package:fortress_mobile/core/app_theme.dart';
import 'package:fortress_mobile/services/api_service.dart';
import 'package:fortress_mobile/screens/dashboard/dashboard_screen.dart';

class SpecializationPinScreen extends StatefulWidget {
  const SpecializationPinScreen({super.key});

  @override
  State<SpecializationPinScreen> createState() => _SpecializationPinScreenState();
}

class _SpecializationPinScreenState extends State<SpecializationPinScreen> {
  String? _selectedType;
  final List<String> _selectedSubtypes = [];
  final _pinController = TextEditingController();
  final _confirmPinController = TextEditingController();
  bool _isLoading = false;

  final List<String> _types = ['Medical Relief', 'Education', 'Disaster Response', 'Food Security'];
  final List<String> _subtypes = ['Oxygen', 'Blood', 'Tents', 'Ambulance', 'Surgical Aid', 'Vaccines'];

  @override
  void dispose() {
    _pinController.dispose();
    _confirmPinController.dispose();
    super.dispose();
  }

  void _showSubtypePopup() {
    showDialog(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setPopupState) {
          return AlertDialog(
            backgroundColor: AppTheme.surfaceColor,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppTheme.borderRadius)),
            title: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text('Ngo Subtype', style: TextStyle(color: Colors.white)),
                IconButton(
                  icon: const Icon(Icons.cancel_rounded, color: Colors.grey),
                  onPressed: () => Navigator.of(context).pop(),
                ),
              ],
            ),
            content: SizedBox(
              width: double.maxFinite,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Text('Select up to 5 tags', style: TextStyle(fontSize: 12, color: Colors.white54)),
                  const SizedBox(height: 16),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: _subtypes.map((tag) {
                      final isSelected = _selectedSubtypes.contains(tag);
                      return FilterChip(
                        label: Text(tag),
                        selected: isSelected,
                        onSelected: (val) {
                          if (_selectedSubtypes.length >= 5 && val) return;
                          setPopupState(() {
                            if (val) {
                              _selectedSubtypes.add(tag);
                            } else {
                              _selectedSubtypes.remove(tag);
                            }
                          });
                          setState(() {}); // Update main screen
                        },
                        selectedColor: AppTheme.primaryColor.withOpacity(0.2),
                        checkmarkColor: AppTheme.primaryColor,
                      );
                    }).toList(),
                  ),
                ],
              ),
            ),
          );
        }
      ),
    );
  }

  Future<void> _onSubmit() async {
    if (_selectedType == null || _selectedSubtypes.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('NGO Type and at least one Subtype tag are mandatory!'), backgroundColor: Colors.red),
      );
      return;
    }
    if (_pinController.text.length < 6 || _pinController.text != _confirmPinController.text) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Check your PIN. It must be 6 digits and match the confirmation.'), backgroundColor: Colors.red),
      );
      return;
    }

    setState(() { _isLoading = true; });

    try {
      final String dummyUid = 'NGO-UID-${DateTime.now().millisecondsSinceEpoch}';
      final String dummyRegNo = 'REG-${DateTime.now().millisecondsSinceEpoch.toString().substring(5)}';

      // 1. Signup NGO Admin
      await ApiService.signupNGOAdmin({
        'uid': dummyUid,
        'name': 'Demo NGO Admin',
        'email': 'admin@demo-ngo.org',
        'phone': '+919999988888',
        'ngo_reg_no': dummyRegNo,
        'region': 'MUMBAI',
        'tier': 1,
        'ngo_type': _selectedType,
        'ngo_tags': _selectedSubtypes,
      });

      // 2. Setup PIN
      await ApiService.setupPIN(dummyUid, _pinController.text);

      if (!mounted) return;

      // 3. Navigate to Dashboard
      Navigator.of(context).pushAndRemoveUntil(
        MaterialPageRoute(builder: (context) => const DashboardScreen(
          role: 'NGO_ADMIN',
          userName: 'Demo NGO Admin',
        )),
        (route) => false,
      );
    } catch (e) {
      if (!mounted) return;
      setState(() { _isLoading = false; });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('NGO Signup Failed: $e'), backgroundColor: Colors.red),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Final Step'),
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new_rounded, color: Colors.white),
          onPressed: () => Navigator.of(context).pop(),
        ),
      ),
      body: Column(
        children: [
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(24.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('NGO Niche & Security', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: AppTheme.primaryColor)),
                  const SizedBox(height: 8),
                  const Text('* all fields are mandatory', style: TextStyle(color: Colors.redAccent, fontSize: 12)),
                  const SizedBox(height: 32),
                  
                  const Text('NGO Type: *', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white)),
                  const SizedBox(height: 8),
                  _buildDropdown(),
                  
                  const SizedBox(height: 24),
                  const Text('Ngo Subtype: *', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white)),
                  const SizedBox(height: 8),
                  _buildSubtypeBox(),
                  
                  const SizedBox(height: 32),
                  const Text('Set 6 digit pin *', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white)),
                  _buildPinField(_pinController),
                  const SizedBox(height: 16),
                  const Text('Confirm pin *', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white)),
                  _buildPinField(_confirmPinController),
                  
                  const SizedBox(height: 48),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      TextButton(
                        onPressed: () => Navigator.of(context).pop(),
                        child: const Text('Previous', style: TextStyle(color: Colors.white54)),
                      ),
                      ElevatedButton(
                        style: ElevatedButton.styleFrom(
                          minimumSize: const Size(120, 50),
                          backgroundColor: AppTheme.primaryColor,
                          foregroundColor: Colors.black,
                        ),
                        onPressed: _onSubmit,
                        child: const Text('Submit'),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
          _buildProgressDots(3),
        ],
      ),
    );
  }


  Widget _buildDropdown() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(AppTheme.borderRadius),
        border: Border.all(color: Colors.grey.withOpacity(0.2)),
      ),
      child: DropdownButtonHideUnderline(
        child: DropdownButton<String>(
          value: _selectedType,
          isExpanded: true,
          hint: const Text('Select NGO Category'),
          items: _types.map((e) => DropdownMenuItem(value: e, child: Text(e))).toList(),
          onChanged: (val) => setState(() => _selectedType = val),
        ),
      ),
    );
  }

  Widget _buildSubtypeBox() {
    return InkWell(
      onTap: _showSubtypePopup,
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(AppTheme.borderRadius),
          border: Border.all(color: Colors.grey.withOpacity(0.2)),
        ),
        child: _selectedSubtypes.isEmpty
            ? const Text('Click to select tags', style: TextStyle(color: Colors.grey))
            : Wrap(
                spacing: 8,
                runSpacing: 8,
                children: _selectedSubtypes.map((tag) => Chip(
                  label: Text(tag, style: const TextStyle(fontSize: 12)),
                  deleteIcon: const Icon(Icons.cancel, size: 16),
                  onDeleted: () => setState(() => _selectedSubtypes.remove(tag)),
                )).toList(),
              ),
      ),
    );
  }

  Widget _buildPinField(TextEditingController controller) {
    return TextField(
      controller: controller,
      obscureText: true,
      keyboardType: TextInputType.number,
      maxLength: 6,
      decoration: const InputDecoration(
        counterText: '',
        hintText: '● ● ● ● ● ●',
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

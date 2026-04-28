import 'package:flutter/material.dart';
import 'package:fortress_mobile/core/app_theme.dart';
import 'package:fortress_mobile/services/api_service.dart';

/// Phase 6: The "Raise Request" Flow (Screen 17) - Citizen Only
class RaiseRequestPage extends StatefulWidget {
  final VoidCallback onSuccess;

  const RaiseRequestPage({super.key, required this.onSuccess});

  @override
  State<RaiseRequestPage> createState() => _RaiseRequestPageState();
}

class _RaiseRequestPageState extends State<RaiseRequestPage> {
  String? _selectedType;
  final List<String> _selectedSubtypes = [];
  final _messageController = TextEditingController();
  bool _isUploading = false;
  String? _attachedFileName;

  final List<String> _ngoTypes = [
    'Medical Relief',
    'Disaster Response',
    'Food Security',
    'Education',
    'Social Support',
    'Animal Welfare'
  ];

  final List<String> _subtypes = [
    'Oxygen', 'Blood', 'Ambulance', 'Tents', 'Dry Ration', 'Cooked Food',
    'Rescue', 'First Aid', 'Medicines', 'Water', 'Clothing', 'Shelter'
  ];

  @override
  void dispose() {
    _messageController.dispose();
    super.dispose();
  }

  void _onUpload() {
    // Logic: 2MB limit enforcement would happen here
    setState(() {
      _attachedFileName = "report_document.pdf (1.2MB)";
    });
  }

  Future<void> _submitRequest() async {
    if (_selectedType == null || _selectedSubtypes.isEmpty || _messageController.text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please fill all mandatory fields.'), backgroundColor: Colors.red),
      );
      return;
    }

    setState(() { _isUploading = true; });

    try {
      final payload = {
        'card_type': 'CITIZEN_SERVICE', // Default for now
        'ngo_type': _selectedType,
        'ngo_tags': _selectedSubtypes,
        'message': _messageController.text,
        'attachment': _attachedFileName, // Usually an uploaded URL, sending string for now
        'quantity': 1,
      };

      await ApiService.createRequest(payload);

      if (!mounted) return;
      // Clear Form & Return to Home
      setState(() {
        _selectedType = null;
        _selectedSubtypes.clear();
        _messageController.clear();
        _attachedFileName = null;
        _isUploading = false;
      });

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Request Raised Successfully!'), backgroundColor: AppTheme.tealPrimary),
      );

      widget.onSuccess(); // Triggers navigation back to Home tab
    } catch (e) {
      if (!mounted) return;
      setState(() { _isUploading = false; });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to raise request: $e'), backgroundColor: Colors.red),
      );
    }
  }

  void _showSubtypePopup() {
    showDialog(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setPopupState) {
          return AlertDialog(
            backgroundColor: Colors.white,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            title: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text('Ngo Subtype', style: TextStyle(color: AppTheme.navySecondary, fontWeight: FontWeight.bold)),
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
                  const Text('Select up to 5 tags', style: TextStyle(fontSize: 12, color: Colors.grey)),
                  const SizedBox(height: 16),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: _subtypes.map((tag) {
                      final isSelected = _selectedSubtypes.contains(tag);
                      return FilterChip(
                        label: Text(tag, style: TextStyle(color: isSelected ? Colors.white : Colors.black87)),
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
                        selectedColor: AppTheme.tealPrimary,
                        checkmarkColor: Colors.white,
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

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Raise a Request',
            style: TextStyle(
              color: AppTheme.navySecondary,
              fontSize: 22,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 8),
          const Text(
            'Submit your request to the dispatch agent.',
            style: TextStyle(color: Colors.grey, fontSize: 14),
          ),
          const SizedBox(height: 32),

          // 1. NGO Type Dropdown
          const Text('Select NGO Type *', style: TextStyle(fontWeight: FontWeight.bold, color: AppTheme.navySecondary)),
          const SizedBox(height: 8),
          _buildDropdown(),

          const SizedBox(height: 24),

          // 2. Subtype Tags with + Icon
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text('Select Subtypes (Max 5) *', style: TextStyle(fontWeight: FontWeight.bold, color: AppTheme.navySecondary)),
              IconButton(
                onPressed: _showSubtypePopup,
                icon: const Icon(Icons.add_circle_outline_rounded, color: AppTheme.tealPrimary),
              ),
            ],
          ),
          const SizedBox(height: 8),
          _buildSubtypeBox(),

          const SizedBox(height: 24),

          // 3. Message Box
          const Text('Message / Description *', style: TextStyle(fontWeight: FontWeight.bold, color: AppTheme.navySecondary)),
          const SizedBox(height: 8),
          TextField(
            controller: _messageController,
            maxLines: 5,
            decoration: InputDecoration(
              hintText: 'Enter details of your request...',
              fillColor: Colors.white,
              filled: true,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12),
                borderSide: BorderSide(color: Colors.grey.withOpacity(0.2)),
              ),
            ),
          ),

          const SizedBox(height: 24),

          // 4. Attachment Button
          const Text('Attachment (Max 2MB)', style: TextStyle(fontWeight: FontWeight.bold, color: AppTheme.navySecondary)),
          const SizedBox(height: 8),
          InkWell(
            onTap: _onUpload,
            child: Container(
              width: double.infinity,
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppTheme.tealPrimary.withOpacity(0.5)),
              ),
              child: Row(
                children: [
                  const Icon(Icons.cloud_upload_outlined, color: AppTheme.tealPrimary),
                  const SizedBox(width: 12),
                  Text(
                    _attachedFileName ?? 'Upload Document / Image',
                    style: TextStyle(color: _attachedFileName != null ? Colors.black87 : Colors.grey),
                  ),
                ],
              ),
            ),
          ),

          const SizedBox(height: 48),

          // Action Buttons
          Row(
            children: [
              Expanded(
                child: OutlinedButton(
                  onPressed: widget.onSuccess,
                  style: OutlinedButton.styleFrom(
                    minimumSize: const Size(0, 56),
                    side: const BorderSide(color: Colors.grey),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                  child: const Text('CANCEL', style: TextStyle(color: Colors.grey)),
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: ElevatedButton(
                  onPressed: _submitRequest,
                  style: ElevatedButton.styleFrom(
                    minimumSize: const Size(0, 56),
                    backgroundColor: AppTheme.tealPrimary,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                  child: const Text('SUBMIT'),
                ),
              ),
            ],
          ),
          const SizedBox(height: 40),
        ],
      ),
    );
  }

  Widget _buildDropdown() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.grey.withOpacity(0.2)),
      ),
      child: DropdownButtonHideUnderline(
        child: DropdownButton<String>(
          value: _selectedType,
          isExpanded: true,
          hint: const Text('Select Category'),
          items: _ngoTypes.map((e) => DropdownMenuItem(value: e, child: Text(e))).toList(),
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
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Colors.grey.withOpacity(0.2)),
        ),
        child: _selectedSubtypes.isEmpty
            ? const Text('Click + to select tags', style: TextStyle(color: Colors.grey))
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
}

}

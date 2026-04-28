import 'package:flutter/material.dart';
import 'package:fortress_mobile/core/app_theme.dart';

class GiftInKindPopup extends StatefulWidget {
  final List<String> requestedItems;
  final Function(Map<String, int>) onConfirm;

  const GiftInKindPopup({
    super.key,
    required this.requestedItems,
    required this.onConfirm,
  });

  @override
  State<GiftInKindPopup> createState() => _GiftInKindPopupState();
}

class _GiftInKindPopupState extends State<GiftInKindPopup> {
  final Map<String, int> _selectedItems = {};
  final Map<String, bool> _activeSelections = {};

  @override
  void initState() {
    super.initState();
    for (var item in widget.requestedItems) {
      _activeSelections[item] = false;
      _selectedItems[item] = 0; 
    }
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: Colors.transparent,
      insetPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
      child: Container(
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(24),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.2),
              blurRadius: 30,
              offset: const Offset(0, 10),
            ),
          ],
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            _buildHeader(),
            _buildContent(),
            _buildFooter(),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: AppTheme.tealPrimary.withOpacity(0.05),
        borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: AppTheme.tealPrimary.withOpacity(0.1),
              shape: BoxShape.circle,
            ),
            child: const Icon(Icons.inventory_2_outlined, color: AppTheme.tealPrimary, size: 28),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'GIFT IN KIND',
                  style: TextStyle(
                    fontWeight: FontWeight.w900,
                    fontSize: 22,
                    color: AppTheme.navySecondary,
                    letterSpacing: -0.5,
                  ),
                ),
                Text(
                  'Resource Fulfillment Portal',
                  style: TextStyle(color: Colors.grey[600], fontSize: 13, fontWeight: FontWeight.w500),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildContent() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'SELECT CONTRIBUTIONS',
            style: TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w900,
              color: Colors.grey,
              letterSpacing: 1.2,
            ),
          ),
          const SizedBox(height: 16),
          ConstrainedBox(
            constraints: const BoxConstraints(maxHeight: 300),
            child: ListView.builder(
              shrinkWrap: true,
              itemCount: widget.requestedItems.length,
              itemBuilder: (context, index) {
                final item = widget.requestedItems[index];
                final bool isActive = _activeSelections[item] ?? false;
                
                return AnimatedContainer(
                  duration: const Duration(milliseconds: 200),
                  margin: const EdgeInsets.only(bottom: 12),
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  decoration: BoxDecoration(
                    color: isActive ? AppTheme.tealPrimary.withOpacity(0.02) : Colors.transparent,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(
                      color: isActive ? AppTheme.tealPrimary.withOpacity(0.3) : Colors.grey.withOpacity(0.15),
                      width: isActive ? 1.5 : 1.0,
                    ),
                  ),
                  child: Row(
                    children: [
                      _buildCheckbox(item, isActive),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Text(
                          item,
                          style: TextStyle(
                            fontWeight: isActive ? FontWeight.w900 : FontWeight.w600,
                            color: isActive ? AppTheme.navySecondary : Colors.grey[700],
                            fontSize: 15,
                          ),
                        ),
                      ),
                      if (isActive) _buildQuantityInput(item),
                    ],
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCheckbox(String item, bool isActive) {
    return GestureDetector(
      onTap: () => setState(() => _activeSelections[item] = !isActive),
      child: Container(
        width: 24,
        height: 24,
        decoration: BoxDecoration(
          color: isActive ? AppTheme.tealPrimary : Colors.transparent,
          borderRadius: BorderRadius.circular(6),
          border: Border.all(
            color: isActive ? AppTheme.tealPrimary : Colors.grey[400]!,
            width: 2,
          ),
        ),
        child: isActive ? const Icon(Icons.check, color: Colors.white, size: 16) : null,
      ),
    );
  }

  Widget _buildQuantityInput(String item) {
    return Container(
      width: 90,
      height: 40,
      padding: const EdgeInsets.symmetric(horizontal: 8),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppTheme.tealPrimary.withOpacity(0.5)),
      ),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              keyboardType: TextInputType.number,
              style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14),
              decoration: const InputDecoration(
                isDense: true,
                border: InputBorder.none,
                hintText: '0',
              ),
              onChanged: (val) {
                _selectedItems[item] = int.tryParse(val) ?? 0;
              },
            ),
          ),
          const Text(
            'UNIT',
            style: TextStyle(fontSize: 9, fontWeight: FontWeight.w900, color: AppTheme.tealPrimary),
          ),
        ],
      ),
    );
  }

  Widget _buildFooter() {
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Row(
        children: [
          Expanded(
            child: TextButton(
              onPressed: () => Navigator.pop(context),
              style: TextButton.styleFrom(
                foregroundColor: Colors.grey[600],
                padding: const EdgeInsets.symmetric(vertical: 16),
              ),
              child: const Text('CANCEL', style: TextStyle(fontWeight: FontWeight.w900)),
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: ElevatedButton(
              onPressed: () {
                final confirmed = <String, int>{};
                _activeSelections.forEach((key, value) {
                  if (value && (_selectedItems[key] ?? 0) > 0) {
                    confirmed[key] = _selectedItems[key]!;
                  }
                });
                if (confirmed.isNotEmpty) {
                  widget.onConfirm(confirmed);
                  Navigator.pop(context);
                }
              },
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.tealPrimary,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 16),
                elevation: 4,
                shadowColor: AppTheme.tealPrimary.withOpacity(0.3),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
              child: const Text('CONFIRM SUPPLY', style: TextStyle(fontWeight: FontWeight.w900)),
            ),
          ),
        ],
      ),
    );
  }
}


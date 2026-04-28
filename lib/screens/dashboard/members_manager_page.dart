import 'package:flutter/material.dart';
import 'package:fortress_mobile/core/app_theme.dart';

class MembersManagerPage extends StatefulWidget {
  final String role; // 'NGO_ADMIN' or others

  const MembersManagerPage({super.key, required this.role});

  @override
  State<MembersManagerPage> createState() => _MembersManagerPageState();
}

class _MembersManagerPageState extends State<MembersManagerPage> {
  // Mock Team Data (Will be replaced by API)
  final List<Map<String, dynamic>> _members = [
    {'uid': '1', 'name': 'Rahul Sharma', 'rank': 'Power Group', 'hasDispatch': true},
    {'uid': '2', 'name': 'Priya Patel', 'rank': 'Member', 'hasDispatch': false},
    {'uid': '3', 'name': 'Vikram Singh', 'rank': 'Member', 'hasDispatch': false},
    {'uid': '4', 'name': 'Sneha K.', 'rank': 'Power Group', 'hasDispatch': true},
  ];

  @override
  Widget build(BuildContext context) {
    bool isAdmin = widget.role == 'NGO_ADMIN';

    return Column(
      children: [
        _buildFilters(),
        Expanded(
          child: ListView.separated(
            padding: const EdgeInsets.all(24.0),
            itemCount: _members.length,
            separatorBuilder: (context, index) => const SizedBox(height: 16),
            itemBuilder: (context, index) {
              final member = _members[index];
              return _buildMemberCard(member, isAdmin);
            },
          ),
        ),
      ],
    );
  }

  Widget _buildFilters() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
      color: Colors.white,
      child: Row(
        children: [
          _filterButton('Rank', true),
          const SizedBox(width: 12),
          _filterButton('Power', false),
          const Spacer(),
          Text(
            '${_members.length} Members',
            style: TextStyle(color: AppTheme.navySecondary.withOpacity(0.5), fontSize: 12),
          ),
        ],
      ),
    );
  }

  Widget _filterButton(String label, bool isSelected) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      decoration: BoxDecoration(
        color: isSelected ? AppTheme.tealPrimary : Colors.transparent,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: isSelected ? AppTheme.tealPrimary : Colors.grey.shade300),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: isSelected ? Colors.white : AppTheme.navySecondary,
          fontWeight: FontWeight.bold,
          fontSize: 12,
        ),
      ),
    );
  }

  Widget _buildMemberCard(Map<String, dynamic> member, bool isAdmin) {
    bool isPowerGroup = member['rank'] == 'Power Group';

    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: Colors.grey.shade100),
        boxShadow: [
          BoxShadow(color: AppTheme.navySecondary.withOpacity(0.04), blurRadius: 20, offset: const Offset(0, 10)),
        ],
      ),
      child: Row(
        children: [
          Container(
            width: 50,
            height: 50,
            decoration: BoxDecoration(
              gradient: LinearGradient(colors: [AppTheme.tealPrimary.withOpacity(0.1), Colors.white]),
              shape: BoxShape.circle,
            ),
            child: Center(
              child: Text(member['name'][0], style: const TextStyle(color: AppTheme.tealPrimary, fontWeight: FontWeight.w900, fontSize: 18)),
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(member['name'], style: const TextStyle(fontWeight: FontWeight.w900, color: AppTheme.navySecondary, fontSize: 15)),
                const SizedBox(height: 6),
                _buildRankTag(member, isAdmin),
              ],
            ),
          ),
          _buildDispatchControl(member, isAdmin, isPowerGroup),
          if (isAdmin)
            Padding(
              padding: const EdgeInsets.only(left: 8),
              child: IconButton(
                icon: Icon(Icons.remove_circle_outline_rounded, color: Colors.red.withOpacity(0.4), size: 20),
                onPressed: () => _confirmRemoval(member['name']),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildRankTag(Map<String, dynamic> member, bool isAdmin) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: AppTheme.backgroundGray,
        borderRadius: BorderRadius.circular(8),
      ),
      child: DropdownButtonHideUnderline(
        child: DropdownButton<String>(
          value: member['rank'],
          dropdownColor: Colors.white,
          borderRadius: BorderRadius.circular(16),
          items: ['Member', 'Power Group'].map((String value) {
            return DropdownMenuItem<String>(
              value: value,
              child: Text(value, style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700)),
            );
          }).toList(),
          onChanged: isAdmin ? (newRank) {
            setState(() {
              member['rank'] = newRank;
              if (newRank == 'Member') member['hasDispatch'] = false;
            });
          } : null,
          icon: const Icon(Icons.expand_more_rounded, size: 14),
          style: const TextStyle(color: AppTheme.navySecondary),
        ),
      ),
    );
  }

  Widget _buildDispatchControl(Map<String, dynamic> member, bool isAdmin, bool isPowerGroup) {
    return Column(
      children: [
        Transform.scale(
          scale: 0.8,
          child: Switch(
            value: member['hasDispatch'],
            onChanged: (isAdmin && isPowerGroup) ? (val) {
              setState(() => member['hasDispatch'] = val);
            } : null,
            activeColor: AppTheme.tealPrimary,
            activeTrackColor: AppTheme.tealPrimary.withOpacity(0.2),
          ),
        ),
        Text(
          'DISPATCH',
          style: TextStyle(
            fontSize: 8,
            fontWeight: FontWeight.w900,
            letterSpacing: 1,
            color: isPowerGroup ? AppTheme.tealPrimary : Colors.grey.shade400,
          ),
        ),
      ],
    );
  }

  void _confirmRemoval(String name) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Remove Member?', style: TextStyle(fontWeight: FontWeight.bold)),
        content: Text('Are you sure you want to remove $name from the NGO?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('CANCEL')),
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('REMOVE', style: TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );
  }
}

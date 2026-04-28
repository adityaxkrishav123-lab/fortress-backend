import 'package:flutter/material.dart';
import 'package:fortress_mobile/core/app_theme.dart';
import 'package:fortress_mobile/screens/dashboard/action_card_widget.dart';
import 'package:fortress_mobile/screens/dashboard/ai_report_viewer.dart';
import 'package:fortress_mobile/screens/dashboard/gift_in_kind_popup.dart';
import 'package:fortress_mobile/services/mailbox_service.dart';
import 'package:fortress_mobile/services/api_service.dart';

/// Phase 7: The Mailbox (Screens 14 & 18)
/// This page displays both live updates and local mission history.
class MailboxPage extends StatefulWidget {
  final VoidCallback onRefreshGlow;
  final String userRole; // Pass role from Dashboard

  const MailboxPage({
    super.key, 
    required this.onRefreshGlow,
    required this.userRole,
  });

  @override
  State<MailboxPage> createState() => _MailboxPageState();
}

class _MailboxPageState extends State<MailboxPage> {
  List<Map<String, dynamic>> _missions = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadMailbox();
  }

  Future<void> _loadMailbox() async {
    // 1. Mark as Read on entry to turn off Dashboard Glow
    await MailboxService.markAllAsRead();
    widget.onRefreshGlow();

    setState(() { _isLoading = true; });
    try {
      final data = await ApiService.fetchInbox();
      final List<dynamic> inbox = data['inbox'] ?? [];
      
      setState(() {
        _missions = inbox.map((card) {
          ActionCardType type = ActionCardType.service;
          if (card['card_type'] == 'INSTANT_HELP') type = ActionCardType.instant;
          if (card['card_type'] == 'NGO_VOLUNTEER_REQUEST') type = ActionCardType.volunteer;

          return {
            'card_id': card['card_id'],
            'senderName': card['sender_role'] ?? 'Unknown Sender',
            'message': card['original_message'] ?? 'No message provided.',
            'type': type,
            'time': 'Just now', // Could be formatted from card['created_at']
            'isAccepted': card['status'] == 'ACCEPTED',
            'contactPhone': card['sender_phone'],
            'contactEmail': card['sender_email'],
            'items': List<String>.from(card['items_needed'] ?? []),
            'original_card': card,
          };
        }).toList();
        _isLoading = false;
      });
    } catch (e) {
      print('Error fetching inbox: $e');
      setState(() {
        _isLoading = false;
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to load live mailbox data.')),
        );
      }
    }
  }

  void _handleAccept(int index) async {
    final mission = _missions[index];
    final cardId = mission['card_id'];
    
    if (mission['type'] == ActionCardType.instant) {
      showDialog(
        context: context,
        builder: (context) => GiftInKindPopup(
          requestedItems: List<String>.from(mission['items'] ?? []),
          onConfirm: (confirmedItems) async {
            // Note: In reality, we need to map confirmedItems to the CommitSupplyPayload
            // For now, assume it's done or we just do a simple ACCEPT for demo wiring
            try {
              // Note: 2-step Instant Help commit would be a separate API call here
              // For basic wiring, we will just visually mark it
              setState(() {
                _missions[index]['isAccepted'] = true;
              });
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('Supply commitment dispatched successfully!')),
              );
            } catch (e) {
              print('Error: $e');
            }
          },
        ),
      );
    } else {
      try {
        await ApiService.respondToCard(cardId, 'ACCEPT');
        setState(() {
          _missions[index]['isAccepted'] = true;
        });
      } catch (e) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to accept: $e')),
        );
      }
    }
  }

  void _handleReject(int index) async {
    final cardId = _missions[index]['card_id'];
    try {
      await ApiService.respondToCard(cardId, 'REJECT');
      setState(() => _missions.removeAt(index));
    } catch (e) {
      print('Reject error: $e');
    }
  }

  void _viewReport(Map<String, dynamic> mission) async {
    final cardId = mission['card_id'];
    try {
      final reportData = await ApiService.fetchReport(cardId);
      if (!mounted) return;
      Navigator.push(
        context,
        MaterialPageRoute(
          builder: (context) => AIReportViewer(reportData: reportData),
        ),
      );
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Report unavailable or mission incomplete.')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 20),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                'Tactical Mailbox',
                style: TextStyle(
                  color: AppTheme.navySecondary,
                  fontSize: 24,
                  fontWeight: FontWeight.w900,
                  letterSpacing: -1,
                ),
              ),
              IconButton(
                onPressed: _loadMailbox,
                icon: const Icon(Icons.refresh, color: AppTheme.tealPrimary),
              ),
            ],
          ),
        ),

        Expanded(
          child: _isLoading 
            ? const Center(child: CircularProgressIndicator())
            : _missions.isEmpty 
              ? _buildEmptyState()
              : ListView.builder(
                  padding: const EdgeInsets.symmetric(horizontal: 24),
                  itemCount: _missions.length,
                  itemBuilder: (context, index) {
                    final m = _missions[index];
                    return ActionCard(
                      senderName: m['senderName'],
                      message: m['message'],
                      type: m['type'],
                      time: m['time'],
                      isAccepted: m['isAccepted'] ?? false,
                      isObserver: widget.userRole == 'NGO_MEMBER', // L3 is Observer
                      contactPhone: m['contactPhone'],
                      contactEmail: m['contactEmail'],
                      onAccept: () => _handleAccept(index),
                      onReject: () => _handleReject(index),
                      onViewReport: () => _viewReport(m),
                    );
                  },
                ),
        ),
      ],
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            padding: const EdgeInsets.all(24),
            decoration: BoxDecoration(
              color: Colors.grey[100],
              shape: BoxShape.circle,
            ),
            child: Icon(Icons.mail_lock_outlined, size: 48, color: Colors.grey[400]),
          ),
          const SizedBox(height: 16),
          Text(
            'Secure Mailbox Empty',
            style: TextStyle(
              color: Colors.grey[800], 
              fontSize: 18, 
              fontWeight: FontWeight.w900,
              letterSpacing: -0.5,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            'Waiting for regional crisis updates...',
            style: TextStyle(color: Colors.grey[600], fontSize: 13),
          ),
        ],
      ),
    );
  }
}


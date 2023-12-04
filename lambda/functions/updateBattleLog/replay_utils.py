##
## Replay Utils
##

# Battle input type transformation
def transform_battle_input_type(bitype):
  if not isinstance(bitype, str):
    return "?"
  type_map = {
    "[t]クラシック": "C",
    "[t]モダン": "M"
  }
  return type_map.get(bitype, "?")

# Result calculation
def calculate_result(rounds):
  if not isinstance(rounds, list) or len(rounds) <= 1:
    return "Unknown"
  return "lose" if rounds.count(0) >= 2 else "win"

# ReplayReduced creation
def transform_to_replay_reduced(replay, my_short_id):
  transformed = {}
  
  player1_info = replay.get('player1_info', {})
  player2_info = replay.get('player2_info', {})
  
  player1 = player1_info.get('player', {})
  player2 = player2_info.get('player', {})

  # determine which player is myself
  my_player_info, opponent_player_info = (player1_info, player2_info) if player1.get('short_id') == my_short_id else (player2_info, player1_info)
  my_player, opponent_player = (player1, player2) if player1.get('short_id') == my_short_id else (player2, player1)

  # Populate the transformed data
  transformed.update({
    'fighter_id': my_player.get('fighter_id', ''),
    'short_id': my_player.get('short_id', ''),
    'platform_name': my_player.get('platform_name', ''),
    'character_name': my_player_info.get('character_name', ''),
    'league_point': my_player_info.get('league_point', ''),
    'battle_input_type_name': transform_battle_input_type(my_player_info.get('battle_input_type_name', '')),
    'round_results': my_player_info.get('round_results', []),
    'opponent': {
        'fighter_id': opponent_player.get('fighter_id', ''),
        'short_id': opponent_player.get('short_id', ''),
        'platform_name': opponent_player.get('platform_name', ''),
        'character_name': opponent_player_info.get('character_name', ''),
        'league_point': opponent_player_info.get('league_point', ''),
        'battle_input_type_name': transform_battle_input_type(opponent_player_info.get('battle_input_type_name', '')),
        'round_results': opponent_player_info.get('round_results', [])
    },
    'result': calculate_result(my_player_info.get('round_results', [])),
    'side': 'player1' if player1.get('short_id') == my_short_id else 'player2',
    'replay_id': replay.get('replay_id', ''),
    'uploaded_at': replay.get('uploaded_at', ''),
    'views': replay.get('views', 0),
    'replay_battle_type_name': replay.get('replay_battle_type_name', '')
  })

  return transformed

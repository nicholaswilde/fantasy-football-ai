import unittest
import pandas as pd
import sys
import os
from unittest.mock import patch

# Add the scripts directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'scripts')))

import analysis

class TestCalculateFantasyPoints(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Initialize globals once for all tests in this class
        analysis.initialize_globals()

    def setUp(self):
        # Store original _SCORING_RULES and _CONFIG to restore after tests
        self._original_scoring_rules = analysis._SCORING_RULES.copy()
        # Ensure _CONFIG is a dict before copying, as it might be a MockConfig from a previous test
        if not isinstance(analysis._CONFIG, dict):
            analysis.initialize_globals() # Re-initialize if it's not a dict
        self._original_config = analysis._CONFIG.copy()

    def tearDown(self):
        # Restore original _SCORING_RULES and _CONFIG
        analysis._SCORING_RULES.clear()
        analysis._SCORING_RULES.update(self._original_scoring_rules)
        analysis._CONFIG.clear()
        analysis._CONFIG.update(self._original_config)

    def test_basic_scoring(self):
        # Temporarily modify _SCORING_RULES for this test
        analysis._SCORING_RULES.clear()
        analysis._SCORING_RULES.update({
            'every_25_passing_yards': 1.0,
            'td_pass': 4.0,
            'interceptions_thrown': -2.0,
            'every_10_rushing_yards': 1.0,
            'td_rush': 6.0,
            'every_10_receiving_yards': 1.0,
            'td_reception': 6.0,
            'every_5_receptions': 1.0,
            'total_fumbles_lost': -2.0
        })

        data = {
            'player_name': ['QB1', 'RB1', 'WR1'],
            'position': ['QB', 'RB', 'WR'], # Add position column
            'passing_yards': [250, 0, 0],
            'passing_tds': [2, 0, 0],
            'interceptions': [1, 0, 0],
            'rushing_yards': [0, 100, 0],
            'rushing_tds': [0, 1, 0],
            'receiving_yards': [0, 0, 50],
            'receiving_tds': [0, 0, 1],
            'receptions': [0, 0, 5],
            'rushing_fumbles_lost': [0, 1, 0],
            'receiving_fumbles_lost': [0, 0, 0]
        }
        df = pd.DataFrame(data)
        df = analysis.calculate_fantasy_points(df)

        # Expected points:
        # QB1: (250/25)*1 + 2*4 + 1*(-2) = 10 + 8 - 2 = 16
        # RB1: (100/10)*1 + 1*6 + 1*(-2) = 10 + 6 - 2 = 14
        # WR1: (50/10)*1 + 1*6 + (5/5)*1 = 5 + 6 + 1 = 12
        self.assertAlmostEqual(df.loc[df['player_name'] == 'QB1', 'fantasy_points'].iloc[0], 16.0)
        self.assertAlmostEqual(df.loc[df['player_name'] == 'RB1', 'fantasy_points'].iloc[0], 14.0)
        self.assertAlmostEqual(df.loc[df['player_name'] == 'WR1', 'fantasy_points'].iloc[0], 12.0)

    def test_empty_dataframe(self):
        df = pd.DataFrame()
        df = analysis.calculate_fantasy_points(df)
        self.assertTrue(df.empty)

    def test_missing_columns(self):
        # Temporarily modify _SCORING_RULES for this test
        analysis._SCORING_RULES.clear()
        analysis._SCORING_RULES.update({
            'every_25_passing_yards': 1.0,
            'td_pass': 4.0
        })
        data = {
            'player_name': ['QB1'],
            'passing_yards': [250] # missing passing_tds
        }
        df = pd.DataFrame(data)
        df = analysis.calculate_fantasy_points(df)
        self.assertAlmostEqual(df.loc[df['player_name'] == 'QB1', 'fantasy_points'].iloc[0], 10.0) # Only passing_yards should count

    def test_kicking_scoring(self):
        # Temporarily modify _SCORING_RULES for this test
        analysis._SCORING_RULES.clear()
        analysis._SCORING_RULES.update({
            'fg_made_(60+_yards)': 5.0,
            'fg_made_(50_59_yards)': 5.0,
            'fg_made_(40_49_yards)': 3.0,
            'fg_made_(0_39_yards)': 3.0,
            'fg_missed_(0_39_yards)': -1.0,
            'each_pat_made': 1.0,
            'each_pat_missed': -1.0
        })
        data = {
            'player_name': ['K1'],
            'position': ['K'],
            'madeFieldGoalsFrom50Plus': [1],
            'madeFieldGoalsFrom40To49': [1],
            'madeFieldGoalsFromUnder40': [1],
            'missedFieldGoals': [1],
            'madeExtraPoints': [2],
            'missedExtraPoints': [1]
        }
        df = pd.DataFrame(data)
        df = analysis.calculate_fantasy_points(df)
        # Expected points: (1*5) + (1*3) + (1*3) + (1*-1) + (2*1) + (1*-1) = 5 + 3 + 3 - 1 + 2 - 1 = 11
        self.assertAlmostEqual(df.loc[df['player_name'] == 'K1', 'fantasy_points'].iloc[0], 11.0)

    def test_dst_scoring(self):
        # Temporarily modify _SCORING_RULES for this test
        analysis._SCORING_RULES.clear()
        analysis._SCORING_RULES.update({
            '1_2_sack': 0.5,
            'each_interception': 3.0,
            'each_fumble_recovered': 2.0,
            'blocked_punt,_pat_or_fg': 2.0,
            'defensive_touchdowns': 6.0,
            'each_fumble_forced': 1.0,
            'assisted_tackles': 0.5,
            'solo_tackles': 0.75,
            'passes_defensed': 1.0,
            '0_points_allowed': 10.0,
            '1_6_points_allowed': 7.5,
            '7_13_points_allowed': 5.0,
            '14_17_points_allowed': 2.5,
            '22_27_points_allowed': -2.5,
            '28_34_points_allowed': -5.0,
            '35_45_points_allowed': -7.5,
            '46+_points_allowed': -10.0,
            'less_than_100_total_yards_allowed': 10.0,
            '100_199_total_yards_allowed': 7.5,
            '200_299_total_yards_allowed': 5.0,
            '300_349_total_yards_allowed': 2.5,
            '400_449_total_yards_allowed': -2.5,
            '450_499_total_yards_allowed': -7.5,
            '500_549_total_yards_allowed': -15.0,
            '550+_total_yards_allowed': -25.0
        })
        data = {
            'player_name': ['DST1'],
            'position': ['DST'],
            'defensiveSacks': [2],
            'defensiveInterceptions': [1],
            'defensiveFumbles': [1],
            'defensiveBlockedKicks': [1],
            'defensiveTouchdowns': [1],
            'defensiveForcedFumbles': [1],
            'defensiveAssistedTackles': [2],
            'defensiveSoloTackles': [4],
            'defensivePassesDefensed': [3],
            'defensivePointsAllowed': [10],
            'defensiveYardsAllowed': [250]
        }
        df = pd.DataFrame(data)
        df = analysis.calculate_fantasy_points(df)
        # Expected points:
        # Sacks: 2 * 0.5 = 1
        # Interceptions: 1 * 3 = 3
        # Fumbles Recovered: 1 * 2 = 2
        # Blocked Kicks: 1 * 2 = 2
        # Defensive TDs: 1 * 6 = 6
        # Forced Fumbles: 1 * 1 = 1
        # Assisted Tackles: 2 * 0.5 = 1
        # Solo Tackles: 4 * 0.75 = 3
        # Passes Defensed: 3 * 1 = 3
        # Points Allowed (10 points): 5.0 (from 7-13 range)
        # Yards Allowed (250 yards): 5.0 (from 200-299 range)
        # Total: 1 + 3 + 2 + 2 + 6 + 1 + 1 + 3 + 3 + 5 + 5 = 32.0
        self.assertAlmostEqual(df.loc[df['player_name'] == 'DST1', 'fantasy_points'].iloc[0], 32.0)

    def test_offensive_bonus_scoring(self):
        # Temporarily modify _SCORING_RULES for this test
        analysis._SCORING_RULES.clear()
        analysis._SCORING_RULES.update({
            'every_25_passing_yards': 1.0,
            'td_pass': 6.0,
            'every_10_rushing_yards': 1.0,
            'td_rush': 6.0,
            'every_10_receiving_yards': 1.0,
            'td_reception': 6.0,
            '40+_yard_td_pass_bonus': 1.0,
            '50+_yard_td_pass_bonus': 2.0,
            '40+_yard_td_rush_bonus': 1.0,
            '50+_yard_td_rush_bonus': 2.0,
            '40+_yard_td_rec_bonus': 1.0,
            '50+_yard_td_rec_bonus': 2.0,
            '100_199_yard_receiving_game': 3.0,
            '200+_yard_receiving_game': 4.0,
            '100_199_yard_rushing_game': 3.0,
            '200+_yard_rushing_game': 4.0,
            '300_399_yard_passing_game': 3.0,
            '400+_yard_passing_game': 4.0
        })
        data = {
            'player_name': ['BonusPlayer'],
            'passing_yards': [350],
            'passing_tds': [1],
            'passing_td_yards': [55], # Triggers 40+ and 50+ yard pass bonus
            'rushing_yards': [150],
            'rushing_tds': [1],
            'rushing_td_yards': [45], # Triggers 40+ yard rush bonus
            'receiving_yards': [210],
            'receiving_tds': [1],
            'receiving_td_yards': [40],
            'receptions': [0],
            'interceptions': [0],
            'rushing_fumbles_lost': [0],
            'receiving_fumbles_lost': [0]
        }
        df = pd.DataFrame(data)
        df = analysis.calculate_fantasy_points(df)

        # Expected points calculation:
        # Passing:
        #   350 passing yards: (350 / 25) * 1.0 = 14.0
        #   1 passing TD: 1 * 6.0 = 6.0
        #   55 yard passing TD: 40+ bonus (1.0) + 50+ bonus (2.0) = 3.0
        #   300-399 passing yards game: 3.0
        # Rushing:
        #   150 rushing yards: (150 / 10) * 1.0 = 15.0
        #   1 rushing TD: 1 * 6.0 = 6.0
        #   45 yard rushing TD: 40+ bonus (1.0)
        #   100-199 rushing yards game: 3.0
        # Receiving:
        #   210 receiving yards: (210 / 10) * 1.0 = 21.0
        #   1 receiving TD: 1 * 6.0 = 6.0
        #   6 receptions: (6 / 5) * 1.0 = 1.2 (assuming every 5 receptions is 1.0 point)
        #   40 yard receiving TD: 40+ bonus (1.0)
        # Fumbles:
        #   1 rushing fumble lost: 1 * -2.0 = -2.0
        # Special Teams:
        #   1 special teams TD: 1 * 6.0 = 6.0
        #   1 2pt return: 1 * 3.0 = 3.0

        # Total: 14.0 + 6.0 + 3.0 + 3.0 + 15.0 + 6.0 + 1.0 + 21.0 + 6.0 + 1.2 + 1.0 - 2.0 + 6.0 + 3.0 = 80.0
        self.assertAlmostEqual(df.loc[df['player_name'] == 'BonusPlayer', 'fantasy_points'].iloc[0], 83.0)

    def test_dst_points_and_yards_allowed_scoring(self):
        # Temporarily modify _SCORING_RULES for this test
        analysis._SCORING_RULES.clear()
        analysis._SCORING_RULES.update({
            '0_points_allowed': 10.0,
            '1_6_points_allowed': 7.5,
            '7_13_points_allowed': 5.0,
            '14_17_points_allowed': 2.5,
            '22_27_points_allowed': -2.5,
            '28_34_points_allowed': -5.0,
            '35_45_points_allowed': -7.5,
            '46+_points_allowed': -10.0,
            'less_than_100_total_yards_allowed': 10.0,
            '100_199_total_yards_allowed': 7.5,
            '200_299_total_yards_allowed': 5.0,
            '300_349_total_yards_allowed': 2.5,
            '400_449_total_yards_allowed': -2.5,
            '450_499_total_yards_allowed': -7.5,
            '500_549_total_yards_allowed': -15.0,
            '550+_total_yards_allowed': -25.0
        })

        # Points Allowed Edge Cases
        # 6 points allowed (upper bound of 1-6 range)
        data_pa_6 = {'player_name': ['DST_PA_6'], 'position': ['DST'], 'defensivePointsAllowed': [6], 'defensiveYardsAllowed': [0]}
        df_pa_6 = analysis.calculate_fantasy_points(pd.DataFrame(data_pa_6))
        self.assertAlmostEqual(df_pa_6.loc[df_pa_6['player_name'] == 'DST_PA_6', 'fantasy_points'].iloc[0], 7.5 + 10.0) # 7.5 + 10.0 (for 0 yards)

        # 7 points allowed (lower bound of 7-13 range)
        data_pa_7 = {'player_name': ['DST_PA_7'], 'position': ['DST'], 'defensivePointsAllowed': [7], 'defensiveYardsAllowed': [0]}
        df_pa_7 = analysis.calculate_fantasy_points(pd.DataFrame(data_pa_7))
        self.assertAlmostEqual(df_pa_7.loc[df_pa_7['player_name'] == 'DST_PA_7', 'fantasy_points'].iloc[0], 5.0 + 10.0)

        # 13 points allowed (upper bound of 7-13 range)
        data_pa_13 = {'player_name': ['DST_PA_13'], 'position': ['DST'], 'defensivePointsAllowed': [13], 'defensiveYardsAllowed': [0]}
        df_pa_13 = analysis.calculate_fantasy_points(pd.DataFrame(data_pa_13))
        self.assertAlmostEqual(df_pa_13.loc[df_pa_13['player_name'] == 'DST_PA_13', 'fantasy_points'].iloc[0], 5.0 + 10.0)

        # 14 points allowed (lower bound of 14-17 range)
        data_pa_14 = {'player_name': ['DST_PA_14'], 'position': ['DST'], 'defensivePointsAllowed': [14], 'defensiveYardsAllowed': [0]}
        df_pa_14 = analysis.calculate_fantasy_points(pd.DataFrame(data_pa_14))
        self.assertAlmostEqual(df_pa_14.loc[df_pa_14['player_name'] == 'DST_PA_14', 'fantasy_points'].iloc[0], 2.5 + 10.0)

        # Yards Allowed Edge Cases
        # 99 yards allowed (upper bound of <100 range)
        data_ya_99 = {'player_name': ['DST_YA_99'], 'position': ['DST'], 'defensivePointsAllowed': [0], 'defensiveYardsAllowed': [99]}
        df_ya_99 = analysis.calculate_fantasy_points(pd.DataFrame(data_ya_99))
        self.assertAlmostEqual(df_ya_99.loc[df_ya_99['player_name'] == 'DST_YA_99', 'fantasy_points'].iloc[0], 10.0 + 10.0)

        # 100 yards allowed (lower bound of 100-199 range)
        data_ya_100 = {'player_name': ['DST_YA_100'], 'position': ['DST'], 'defensivePointsAllowed': [0], 'defensiveYardsAllowed': [100]}
        df_ya_100 = analysis.calculate_fantasy_points(pd.DataFrame(data_ya_100))
        self.assertAlmostEqual(df_ya_100.loc[df_ya_100['player_name'] == 'DST_YA_100', 'fantasy_points'].iloc[0], 10.0 + 7.5)

        # 199 yards allowed (upper bound of 100-199 range)
        data_ya_199 = {'player_name': ['DST_YA_199'], 'position': ['DST'], 'defensivePointsAllowed': [0], 'defensiveYardsAllowed': [199]}
        df_ya_199 = analysis.calculate_fantasy_points(pd.DataFrame(data_ya_199))
        self.assertAlmostEqual(df_ya_199.loc[df_ya_199['player_name'] == 'DST_YA_199', 'fantasy_points'].iloc[0], 10.0 + 7.5)

        # 200 yards allowed (lower bound of 200-299 range)
        data_ya_200 = {'player_name': ['DST_YA_200'], 'position': ['DST'], 'defensivePointsAllowed': [0], 'defensiveYardsAllowed': [200]}
        df_ya_200 = analysis.calculate_fantasy_points(pd.DataFrame(data_ya_200))
        self.assertAlmostEqual(df_ya_200.loc[df_ya_200['player_name'] == 'DST_YA_200', 'fantasy_points'].iloc[0], 10.0 + 5.0)

    def test_offensive_yardage_bonus_edge_cases(self):
        # Temporarily modify _SCORING_RULES for this test
        analysis._SCORING_RULES.clear()
        analysis._SCORING_RULES.update({
            'every_25_passing_yards': 1.0,
            'every_10_rushing_yards': 1.0,
            'every_10_receiving_yards': 1.0,
            '100_199_yard_receiving_game': 3.0,
            '200+_yard_receiving_game': 4.0,
            '100_199_yard_rushing_game': 3.0,
            '200+_yard_rushing_game': 4.0,
            '300_399_yard_passing_game': 3.0,
            '400+_yard_passing_game': 4.0
        })

        # Passing Yardage Edge Cases
        # 299 passing yards (below 300-399 bonus)
        data_pass_299 = {'player_name': ['QB_Pass_299'], 'passing_yards': [299]}
        df_pass_299 = analysis.calculate_fantasy_points(pd.DataFrame(data_pass_299))
        self.assertAlmostEqual(df_pass_299.loc[df_pass_299['player_name'] == 'QB_Pass_299', 'fantasy_points'].iloc[0], (299/25)*1.0)

        # 300 passing yards (lower bound of 300-399 bonus)
        data_pass_300 = {'player_name': ['QB_Pass_300'], 'passing_yards': [300]}
        df_pass_300 = analysis.calculate_fantasy_points(pd.DataFrame(data_pass_300))
        self.assertAlmostEqual(df_pass_300.loc[df_pass_300['player_name'] == 'QB_Pass_300', 'fantasy_points'].iloc[0], (300/25)*1.0 + 3.0)

        # 399 passing yards (upper bound of 300-399 bonus)
        data_pass_399 = {'player_name': ['QB_Pass_399'], 'passing_yards': [399]}
        df_pass_399 = analysis.calculate_fantasy_points(pd.DataFrame(data_pass_399))
        self.assertAlmostEqual(df_pass_399.loc[df_pass_399['player_name'] == 'QB_Pass_399', 'fantasy_points'].iloc[0], (399/25)*1.0 + 3.0)

        # 400 passing yards (lower bound of 400+ bonus)
        data_pass_400 = {'player_name': ['QB_Pass_400'], 'passing_yards': [400]}
        df_pass_400 = analysis.calculate_fantasy_points(pd.DataFrame(data_pass_400))
        self.assertAlmostEqual(df_pass_400.loc[df_pass_400['player_name'] == 'QB_Pass_400', 'fantasy_points'].iloc[0], (400/25)*1.0 + 4.0)

        # Rushing Yardage Edge Cases
        # 99 rushing yards (below 100-199 bonus)
        data_rush_99 = {'player_name': ['RB_Rush_99'], 'rushing_yards': [99]}
        df_rush_99 = analysis.calculate_fantasy_points(pd.DataFrame(data_rush_99))
        self.assertAlmostEqual(df_rush_99.loc[df_rush_99['player_name'] == 'RB_Rush_99', 'fantasy_points'].iloc[0], (99/10)*1.0)

        # 100 rushing yards (lower bound of 100-199 bonus)
        data_rush_100 = {'player_name': ['RB_Rush_100'], 'rushing_yards': [100]}
        df_rush_100 = analysis.calculate_fantasy_points(pd.DataFrame(data_rush_100))
        self.assertAlmostEqual(df_rush_100.loc[df_rush_100['player_name'] == 'RB_Rush_100', 'fantasy_points'].iloc[0], (100/10)*1.0 + 3.0)

        # 199 rushing yards (upper bound of 100-199 bonus)
        data_rush_199 = {'player_name': ['RB_Rush_199'], 'rushing_yards': [199]}
        df_rush_199 = analysis.calculate_fantasy_points(pd.DataFrame(data_rush_199))
        self.assertAlmostEqual(df_rush_199.loc[df_rush_199['player_name'] == 'RB_Rush_199', 'fantasy_points'].iloc[0], (199/10)*1.0 + 3.0)

        # 200 rushing yards (lower bound of 200+ bonus)
        data_rush_200 = {'player_name': ['RB_Rush_200'], 'rushing_yards': [200]}
        df_rush_200 = analysis.calculate_fantasy_points(pd.DataFrame(data_rush_200))
        self.assertAlmostEqual(df_rush_200.loc[df_rush_200['player_name'] == 'RB_Rush_200', 'fantasy_points'].iloc[0], (200/10)*1.0 + 4.0)

        # Receiving Yardage Edge Cases
        # 99 receiving yards (below 100-199 bonus)
        data_rec_99 = {'player_name': ['WR_Rec_99'], 'receiving_yards': [99]}
        df_rec_99 = analysis.calculate_fantasy_points(pd.DataFrame(data_rec_99))
        self.assertAlmostEqual(df_rec_99.loc[df_rec_99['player_name'] == 'WR_Rec_99', 'fantasy_points'].iloc[0], (99/10)*1.0)

        # 100 receiving yards (lower bound of 100-199 bonus)
        data_rec_100 = {'player_name': ['WR_Rec_100'], 'receiving_yards': [100]}
        df_rec_100 = analysis.calculate_fantasy_points(pd.DataFrame(data_rec_100))
        self.assertAlmostEqual(df_rec_100.loc[df_rec_100['player_name'] == 'WR_Rec_100', 'fantasy_points'].iloc[0], (100/10)*1.0 + 3.0)

        # 199 receiving yards (upper bound of 100-199 bonus)
        data_rec_199 = {'player_name': ['WR_Rec_199'], 'receiving_yards': [199]}
        df_rec_199 = analysis.calculate_fantasy_points(pd.DataFrame(data_rec_199))
        self.assertAlmostEqual(df_rec_199.loc[df_rec_199['player_name'] == 'WR_Rec_199', 'fantasy_points'].iloc[0], (199/10)*1.0 + 3.0)

        # 200 receiving yards (lower bound of 200+ bonus)
        data_rec_200 = {'player_name': ['WR_Rec_200'], 'receiving_yards': [200]}
        df_rec_200 = analysis.calculate_fantasy_points(pd.DataFrame(data_rec_200))
        self.assertAlmostEqual(df_rec_200.loc[df_rec_200['player_name'] == 'WR_Rec_200', 'fantasy_points'].iloc[0], (200/10)*1.0 + 4.0)

    def test_fumbles_scoring(self):
        # Temporarily modify _SCORING_RULES for this test
        analysis._SCORING_RULES.clear()
        analysis._SCORING_RULES.update({
            'total_fumbles_lost': -2.0
        })

        data = {
            'player_name': ['RB_Fumble', 'WR_Fumble', 'QB_Fumble'],
            'rushing_fumbles_lost': [1, 0, 0],
            'receiving_fumbles_lost': [0, 1, 0],
            'passing_fumbles_lost': [0, 0, 1] # This column is not explicitly handled in calculate_fantasy_points for fumbles_lost sum
        }
        df = pd.DataFrame(data)
        df = analysis.calculate_fantasy_points(df)

        # The calculate_fantasy_points function sums rushing_fumbles_lost and receiving_fumbles_lost
        # It does not explicitly handle 'passing_fumbles_lost' in the current implementation.
        # So, QB_Fumble should have 0 points from fumbles.
        self.assertAlmostEqual(df.loc[df['player_name'] == 'RB_Fumble', 'fantasy_points'].iloc[0], -2.0)
        self.assertAlmostEqual(df.loc[df['player_name'] == 'WR_Fumble', 'fantasy_points'].iloc[0], -2.0)
        self.assertAlmostEqual(df.loc[df['player_name'] == 'QB_Fumble', 'fantasy_points'].iloc[0], 0.0)

    def test_two_point_conversions(self):
        # Temporarily modify _SCORING_RULES for this test
        analysis._SCORING_RULES.clear()
        analysis._SCORING_RULES.update({
            '2pt_passing_conversion': 2.0,
            '2pt_rushing_conversion': 2.0,
            '2pt_receiving_conversion': 2.0
        })

        data = {
            'player_name': ['QB_2pt', 'RB_2pt', 'WR_2pt'],
            'passing_2pt_conversions': [1, 0, 0],
            'rushing_2pt_conversions': [0, 1, 0],
            'receiving_2pt_conversions': [0, 0, 1]
        }
        df = pd.DataFrame(data)
        df = analysis.calculate_fantasy_points(df)

        self.assertAlmostEqual(df.loc[df['player_name'] == 'QB_2pt', 'fantasy_points'].iloc[0], 2.0)
        self.assertAlmostEqual(df.loc[df['player_name'] == 'RB_2pt', 'fantasy_points'].iloc[0], 2.0)
        self.assertAlmostEqual(df.loc[df['player_name'] == 'WR_2pt', 'fantasy_points'].iloc[0], 2.0)

    def test_special_teams_td_scoring(self):
        # Temporarily modify _SCORING_RULES for this test
        analysis._SCORING_RULES.clear()
        analysis._SCORING_RULES.update({
            'kickoff_return_td': 6.0,
            'punt_return_td': 6.0,
            'interception_return_td': 6.0,
            'fumble_return_td': 6.0,
            'blocked_punt_or_fg_return_for_td': 6.0,
            '2pt_return': 3.0
        })

        data = {
            'player_name': ['ST_Player1', 'ST_Player2'],
            'special_teams_tds': [1, 0],
            'kickoff_return_td': [1, 0],
            'punt_return_td': [0, 1],
            'interception_return_td': [0, 0],
            'fumble_return_td': [0, 0],
            'blocked_punt_or_fg_return_for_td': [0, 0],
            '2pt_return': [0, 1]
        }
        df = pd.DataFrame(data)
        df = analysis.calculate_fantasy_points(df)

        # The current implementation only uses 'special_teams_tds' and maps it to 'kickoff_return_td'
        # It does not differentiate between different types of special teams TDs.
        # So, ST_Player1 should get 6.0 points for special_teams_tds.
        # ST_Player2 should get 0 points from special_teams_tds, but 3.0 from 2pt_return.
        self.assertAlmostEqual(df.loc[df['player_name'] == 'ST_Player1', 'fantasy_points'].iloc[0], 6.0)
        self.assertAlmostEqual(df.loc[df['player_name'] == 'ST_Player2', 'fantasy_points'].iloc[0], 3.0)

    def test_combined_player_stats(self):
        # Temporarily modify _SCORING_RULES for this test
        analysis._SCORING_RULES.clear()
        analysis._SCORING_RULES.update({
            'every_25_passing_yards': 1.0,
            'td_pass': 4.0,
            'interceptions_thrown': -2.0,
            'every_10_rushing_yards': 1.0,
            'td_rush': 6.0,
            'every_10_receiving_yards': 1.0,
            'td_reception': 6.0,
            'every_5_receptions': 1.0,
            'total_fumbles_lost': -2.0,
            '2pt_passing_conversion': 2.0,
            '2pt_rushing_conversion': 2.0,
            '2pt_receiving_conversion': 2.0,
            '40+_yard_td_pass_bonus': 1.0,
            '50+_yard_td_pass_bonus': 2.0,
            '40+_yard_td_rush_bonus': 1.0,
            '50+_yard_td_rush_bonus': 2.0,
            '40+_yard_td_rec_bonus': 1.0,
            '50+_yard_td_rec_bonus': 2.0,
            '100_199_yard_receiving_game': 3.0,
            '200+_yard_receiving_game': 4.0,
            '100_199_yard_rushing_game': 3.0,
            '200+_yard_rushing_game': 4.0,
            '300_399_yard_passing_game': 3.0,
            '400+_yard_passing_game': 4.0,
            'kickoff_return_td': 6.0,
            '2pt_return': 3.0
        })

        data = {
            'player_name': ['HybridPlayer'],
            'position': ['RB'], # Add position column
            'passing_yards': [250],
            'passing_tds': [1],
            'interceptions': [1],
            'passing_2pt_conversions': [1],
            'passing_td_yards': [55],
            'rushing_yards': [75],
            'rushing_tds': [1],
            'rushing_2pt_conversions': [0],
            'rushing_td_yards': [45],
            'receiving_yards': [120],
            'receiving_tds': [1],
            'receptions': [6],
            'receiving_2pt_conversions': [0],
            'receiving_td_yards': [40],
            'rushing_fumbles_lost': [1],
            'special_teams_tds': [1],
            '2pt_return': [1]
        }
        df = pd.DataFrame(data)
        df = analysis.calculate_fantasy_points(df)

        # Expected points calculation:
        # Passing:
        #   250 passing yards: (250 / 25) * 1.0 = 10.0
        #   1 passing TD: 1 * 4.0 = 4.0
        #   1 interception: 1 * -2.0 = -2.0
        #   1 passing 2pt conversion: 1 * 2.0 = 2.0
        #   55 yard passing TD: 40+ bonus (1.0) + 50+ bonus (2.0) = 3.0
        # Rushing:
        #   75 rushing yards: (75 / 10) * 1.0 = 7.5
        #   1 rushing TD: 1 * 6.0 = 6.0
        #   45 yard rushing TD: 40+ bonus (1.0)
        # Receiving:
        #   120 receiving yards: (120 / 10) * 1.0 = 12.0
        #   1 receiving TD: 1 * 6.0 = 6.0
        #   6 receptions: (6 / 5) * 1.0 = 1.2 (assuming every 5 receptions is 1.0 point)
        #   40 yard receiving TD: 40+ bonus (1.0)
        # Fumbles:
        #   1 rushing fumble lost: 1 * -2.0 = -2.0
        # Special Teams:
        #   1 special teams TD: 1 * 6.0 = 6.0
        #   1 2pt return: 1 * 3.0 = 3.0

        # Total: 10.0 + 4.0 - 2.0 + 2.0 + 3.0 + 7.5 + 6.0 + 1.0 + 12.0 + 6.0 + 1.2 + 1.0 - 2.0 + 6.0 + 3.0 = 61.7
        self.assertAlmostEqual(df.loc[df['player_name'] == 'HybridPlayer', 'fantasy_points'].iloc[0], 61.7)

    def test_negative_scoring_scenarios(self):
        # Temporarily modify _SCORING_RULES for this test
        analysis._SCORING_RULES.clear()
        analysis._SCORING_RULES.update({
            'interceptions_thrown': -3.0,
            'total_fumbles_lost': -2.0,
            'fg_missed_(0_39_yards)': -1.0,
            'each_pat_missed': -1.0,
            '22_27_points_allowed': -2.5,
            '28_34_points_allowed': -5.0,
            '35_45_points_allowed': -7.5,
            '46+_points_allowed': -10.0,
            '400_449_total_yards_allowed': -2.5,
            '450_499_total_yards_allowed': -7.5,
            '500_549_total_yards_allowed': -15.0,
            '550+_total_yards_allowed': -25.0
        })

        # Scenario 1: Offensive player with multiple turnovers
        data_off_neg = {
            'player_name': ['OffensiveNegative'],
            'interceptions': [3],
            'rushing_fumbles_lost': [2],
            'receiving_fumbles_lost': [1]
        }
        df_off_neg = pd.DataFrame(data_off_neg)
        df_off_neg = analysis.calculate_fantasy_points(df_off_neg)
        # Expected: (3 * -3.0) + (3 * -2.0) = -9.0 - 6.0 = -15.0
        self.assertAlmostEqual(df_off_neg.loc[df_off_neg['player_name'] == 'OffensiveNegative', 'fantasy_points'].iloc[0], -15.0)

        # Scenario 2: Kicker with missed kicks
        data_k_neg = {
            'player_name': ['KickerNegative'],
            'position': ['K'],
            'missedFieldGoals': [2],
            'missedExtraPoints': [3]
        }
        df_k_neg = pd.DataFrame(data_k_neg)
        df_k_neg = analysis.calculate_fantasy_points(df_k_neg)
        # Expected: (2 * -1.0) + (3 * -1.0) = -2.0 - 3.0 = -5.0
        self.assertAlmostEqual(df_k_neg.loc[df_k_neg['player_name'] == 'KickerNegative', 'fantasy_points'].iloc[0], -5.0)

        # Scenario 3: DST with high points and yards allowed
        data_dst_neg = {
            'player_name': ['DSTNegative'],
            'position': ['DST'],
            'defensivePointsAllowed': [46],
            'defensiveYardsAllowed': [550]
        }
        df_dst_neg = pd.DataFrame(data_dst_neg)
        df_dst_neg = analysis.calculate_fantasy_points(df_dst_neg)
        # Expected: -10.0 (46+ points allowed) + -25.0 (550+ yards allowed) = -35.0
        self.assertAlmostEqual(df_dst_neg.loc[df_dst_neg['player_name'] == 'DSTNegative', 'fantasy_points'].iloc[0], -35.0)

    def test_get_advanced_draft_recommendations(self):
        # Temporarily modify _SCORING_RULES for this test
        analysis._SCORING_RULES.clear()
        analysis._SCORING_RULES.update({
            'every_25_passing_yards': 1.0,
            'td_pass': 4.0,
            'every_10_rushing_yards': 1.0,
            'td_rush': 6.0,
            'every_10_receiving_yards': 1.0,
            'td_reception': 6.0,
            'every_5_receptions': 1.0
        })

        # Mock analysis.load_config to return a dictionary with league and roster settings
        mock_config_data = {
            'league_settings': {'number_of_teams': 12},
            'roster_settings': {'QB': 1, 'RB': 2, 'WR': 2, 'TE': 1, 'K': 1, 'D_ST': 1}
        }
        with patch('analysis.load_config', return_value=mock_config_data):
            # Re-initialize globals so that _CONFIG gets the mocked data
            analysis.initialize_globals()

            data = {
                'player_name': ['QB1', 'QB1', 'QB2', 'QB2', 'RB1', 'RB1', 'WR1', 'WR1'],
                'position': ['QB', 'QB', 'QB', 'QB', 'RB', 'RB', 'WR', 'WR'],
                'week': [1, 2, 1, 2, 1, 2, 1, 2],
                'fantasy_points': [20, 22, 15, 17, 16, 18, 20, 11.6] # Pre-calculated fantasy points
            }
            df = pd.DataFrame(data)

            recommendations_df = analysis.get_advanced_draft_recommendations(df)

            # Expected VOR and Consistency calculations based on the provided data
            # Overall Fantasy Points:
            # QB1: 20 + 22 = 42
            # QB2: 15 + 17 = 32
            # RB1: 16 + 18 = 34
            # WR1: 20 + 11.6 = 31.6

            # VOR Calculation (using average of top N players as replacement level)
            # QB: Top 12*1 = 12 QBs. Here, only 2 QBs. So replacement level is average of QB1 and QB2.
            # Replacement level avg for QB = (42 + 32) / 2 = 37
            # QB1 VOR = 42 - 37 = 5
            # QB2 VOR = 32 - 37 = -5

            # RB: Top 12*2 = 24 RBs. Here, only 1 RB. So replacement level is RB1 itself.
            # Replacement level avg for RB = 34
            # RB1 VOR = 34 - 34 = 0

            # WR: Top 12*2 = 24 WRs. Here, only 1 WR. So replacement level is WR1 itself.
            # Replacement level avg for WR = 31.6
            # WR1 VOR = 31.6 - 31.6 = 0

            # Consistency (std dev of weekly points)
            # QB1: [20, 22] -> std dev = 1.4142135623730951
            # QB2: [15, 17] -> std dev = 1.4142135623730951
            # RB1: [16, 18] -> std dev = 1.4142135623730951
            # WR1: [20, 11.6] -> std dev = 5.93969690997963

            self.assertFalse(recommendations_df.empty)
            self.assertTrue('vor' in recommendations_df.columns)
            self.assertTrue('consistency_std_dev' in recommendations_df.columns)

            # Verify VOR values
            self.assertAlmostEqual(recommendations_df.loc[recommendations_df['player_name'] == 'QB1', 'vor'].iloc[0], 5.0)
            self.assertAlmostEqual(recommendations_df.loc[recommendations_df['player_name'] == 'QB2', 'vor'].iloc[0], -5.0)
            self.assertAlmostEqual(recommendations_df.loc[recommendations_df['player_name'] == 'RB1', 'vor'].iloc[0], 0.0)
            self.assertAlmostEqual(recommendations_df.loc[recommendations_df['player_name'] == 'WR1', 'vor'].iloc[0], 0.0)

            # Verify consistency values
            self.assertAlmostEqual(recommendations_df.loc[recommendations_df['player_name'] == 'QB1', 'consistency_std_dev'].iloc[0], 1.4142135623730951, places=5)
            self.assertAlmostEqual(recommendations_df.loc[recommendations_df['player_name'] == 'QB2', 'consistency_std_dev'].iloc[0], 1.4142135623730951, places=5)
            self.assertAlmostEqual(recommendations_df.loc[recommendations_df['player_name'] == 'RB1', 'consistency_std_dev'].iloc[0], 1.4142135623730951, places=5)
            self.assertAlmostEqual(recommendations_df.loc[recommendations_df['player_name'] == 'WR1', 'consistency_std_dev'].iloc[0], 5.93969690997963, places=5)

            # Verify sorting (highest VOR first)
            self.assertEqual(recommendations_df.iloc[0]['player_name'], 'QB1')

    def test_zero_stats_player(self):
        # Temporarily modify _SCORING_RULES for this test
        analysis._SCORING_RULES.clear()
        analysis._SCORING_RULES.update({
            'every_25_passing_yards': 1.0,
            'td_pass': 4.0,
            'interceptions_thrown': -2.0,
            'every_10_rushing_yards': 1.0,
            'td_rush': 6.0,
            'every_10_receiving_yards': 1.0,
            'td_reception': 6.0,
            'every_5_receptions': 1.0,
            'total_fumbles_lost': -2.0,
            'fg_made_(60+_yards)': 5.0,
            'fg_made_(50_59_yards)': 5.0,
            'fg_made_(40_49_yards)': 3.0,
            'fg_made_(0_39_yards)': 3.0,
            'fg_missed_(0_39_yards)': -1.0,
            'each_pat_made': 1.0,
            'each_pat_missed': -1.0,
            '1_2_sack': 0.5,
            'each_interception': 3.0,
            'each_fumble_recovered': 2.0,
            'blocked_punt,_pat_or_fg': 2.0,
            'defensive_touchdowns': 6.0,
            'each_fumble_forced': 1.0,
            'assisted_tackles': 0.5,
            'solo_tackles': 0.75,
            'passes_defensed': 1.0,
            '0_points_allowed': 10.0,
            '1_6_points_allowed': 7.5,
            '7_13_points_allowed': 5.0,
            '14_17_points_allowed': 2.5,
            '22_27_points_allowed': -2.5,
            '28_34_points_allowed': -5.0,
            '35_45_points_allowed': -7.5,
            '46+_points_allowed': -10.0,
            'less_than_100_total_yards_allowed': 10.0,
            '100_199_total_yards_allowed': 7.5,
            '200_299_total_yards_allowed': 5.0,
            '300_349_total_yards_allowed': 2.5,
            '400_449_total_yards_allowed': -2.5,
            '450_499_total_yards_allowed': -7.5,
            '500_549_total_yards_allowed': -15.0,
            '550+_total_yards_allowed': -25.0
        })
        data = {
            'player_name': ['ZeroPlayer'],
            'position': ['QB'], # Position doesn't matter for zero stats
            'passing_yards': [0],
            'passing_tds': [0],
            'interceptions': [0],
            'rushing_yards': [0],
            'rushing_tds': [0],
            'receiving_yards': [0],
            'receiving_tds': [0],
            'receptions': [0],
            'rushing_fumbles_lost': [0],
            'receiving_fumbles_lost': [0],
            'madeFieldGoalsFrom50Plus': [0],
            'madeFieldGoalsFrom40To49': [0],
            'madeFieldGoalsFromUnder40': [0],
            'missedFieldGoals': [0],
            'madeExtraPoints': [0],
            'missedExtraPoints': [0],
            'defensiveSacks': [0],
            'defensiveInterceptions': [0],
            'defensiveFumbles': [0],
            'defensiveBlockedKicks': [0],
            'defensiveTouchdowns': [0],
            'defensiveForcedFumbles': [0],
            'defensiveAssistedTackles': [0],
            'defensiveSoloTackles': [0],
            'defensivePassesDefensed': [0],
            'defensivePointsAllowed': [0],
            'defensiveYardsAllowed': [0]
        }
        df = pd.DataFrame(data)
        df = analysis.calculate_fantasy_points(df)
        self.assertAlmostEqual(df.loc[df['player_name'] == 'ZeroPlayer', 'fantasy_points'].iloc[0], 0.0)

if __name__ == '__main__':
    unittest.main()
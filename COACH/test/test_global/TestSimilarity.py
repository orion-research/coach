"""
Created on 27 juil. 2017

@author: francois
"""
import os
import sys
import unittest

from enum import Enum

sys.path.append(os.path.join(os.curdir, os.pardir, os.pardir, os.pardir))
from COACH.test.test_global.TestGlobal import TestGlobal

class TestSimilarity(TestGlobal):
    #Global
    CASE_NAME_1 = "Case similarity 1"
    CASE_NAME_2 = "Case similarity 2"
    CASE_NAME_3 = "Case similarity 3"
    CASE_NAME_4 = "Case similarity 4"
    SIMILARITY_VALUE_FORMATTER = "{0:.4f}"
    Context_category = Enum("Context_category", ["ORGANIZATION", "PRODUCT", "STAKEHOLDER", "METHOD", "BUSINESS"])
    
    #compute_similarity_dialogue.html
    COMPUTE_SIMILARITY__SIMILARITY_THRESHOLD_FIELD_NAME = "similarity_threshold"
    COMPUTE_SIMILARITY__NUMBER_RATIO_THRESHOLD_FIELD_NAME = "number_ratio_threshold"
    COMPUTE_SIMILARITY__EXPORT_CASE_CHECKBOX_NAME = "export_case"
    
    #computed_similarity.html
    COMPUTED_SIMILARIRY__SUB_TITLE = "Computed similarity"
    
    def setUp(self):
        self.driver.get(self.MAIN_PAGE_ADDRESS)
        self._assert_initial_page()
        self._login()
        self._assert_unactive_case()
        
    def tearDown(self):
        pass
        
        
    def test_similarity(self):
        """
        This method tests macro functionalities of the computing of similarities.
        
        In the following description "identical cases" means two cases with the same goal, context and stakeholders.
            "Same goal" means the same checkbox checked, and the same checkbox unchecked.
            "Same context" means the same single select, multiple select and number (not text).
                "Same single select" means the same option selected, but for "Unknown": 
                        two single select with "Unknown" selected are considered different.
                "Same multiple select" means the same options in the list selected, and the same unselected.
                "Same number" means that the ratio max / min is less than number_ratio_threshold. If min is 0, the numbers are always
                        different (even if max is 0 too).
            "Same stakeholders" means that the same roles appear in both cases. However, it will not checked the multiplicity of the roles.
            
        It will test:
            - Two identical cases have a similarity of 1
            - Two different cases have a similarity less than 1
            - Cases are not returned when their similarity with the current case is below the threshold
            - Number are considered equals when their ratio is below the threshold
            - Number are considered different when their ratio is above the threshold
            - Number are considered as no information if their value is 0
            - A case without information has a similarity of 0 with every case (including another case without information)
            - Several persons with the same role do not bring more information
            - It is possible to retrieve a case where the user is not a stakeholder
            - Export to knowledge repository checkbox
            - A case is not similar to itself
        XXXXX Alternatives, properties and estimations are retrieved for similar cases
        """
        self._open_or_create_case(self.CASE_NAME_1)
        self._set_up_goal()
        self._set_up_context()
        self._set_up_stakeholder()
        self._go_to_link(self.MAIN_MENU__CASE_MENU, self.MAIN_MENU__EXPORT_CASE_LINK, 600)        
         
        # Two identical cases have a similarity of 1
        # A case is not similar to itself
        # Export to knowledge repository checkbox
        self._open_or_create_case(self.CASE_NAME_2)
        self._set_up_goal()
        self._set_up_context()
        self._set_up_stakeholder()
        self._compute_similarity(True)
        self._assert_case_similar(self.CASE_NAME_1, 1)
        self._assert_case_not_similar(self.CASE_NAME_2)
         
        # Several persons with the same role do not bring more information
        self._go_to_link(self.MAIN_MENU__STAKEHOLDERS_MENU, self.MAIN_MENU__STAKEHOLDERS_EDIT)
        # remove "decider" from user1's function, but decider is still in user2's function, so the similarity should not change
        stakeholder_information = self._get_stakeholder_information()
        stakeholder_information[self.INITIAL__USER_NAME_1][self.STAKEHOLDER__ROLE_FUNCTION] = ["Leader"]
        self._save_stakeholders(stakeholder_information)
        self._compute_similarity(True)
        self._assert_case_similar(self.CASE_NAME_1, 1)
         
        # Two different cases have a similarity less than 1
        customer_goal = self._get_goal_category_information(self.GOAL_CATEGORY_CUSTOMER__PREFIX_ID, [1, 2, 3, 15, 16])
        customer_goal = {k: not customer_goal[k] for k in customer_goal}
        self._go_to_link(self.MAIN_MENU__GOAL_MENU, self.MAIN_MENU__GOAL_CUSTOMER_VALUE) 
        self._save_goal_category(customer_goal)
        self._compute_similarity(True)
        self._assert_case_similar(self.CASE_NAME_1, 0.918)
         
        # Cases are not returned when their similarity with the current case is below the threshold 
        self._go_to_link(self.MAIN_MENU__CASE_MENU, self.MAIN_MENU__COMPUTE_SIMILARITY)
        self._compute_similarity(False, 0.95)
        self._assert_case_not_similar(self.CASE_NAME_1)
         
        # Number are considered equals when their ratio is below the threshold
        organization_context = self._get_context_category_information(self.Context_category.ORGANIZATION)
        organization_context["O05.1_integer"] = 100
        self._go_to_link(self.MAIN_MENU__CONTEXT_MENU, self.MAIN_MENU__CONTEXT_ORGANIZATION)
        self._save_category_context(organization_context)
        self._compute_similarity(True, 0.8, 2)
        self._assert_case_similar(self.CASE_NAME_1, 0.918)
         
        # Number are considered different when their ratio is above the threshold
        self._compute_similarity(False, 0.8, 1.5)
        self._assert_case_similar(self.CASE_NAME_1, 0.9016)
         
        # Number are considered as no information if their value is 0
        organization_context["O05.1_integer"] = 0
        self._go_to_link(self.MAIN_MENU__CONTEXT_MENU, self.MAIN_MENU__CONTEXT_ORGANIZATION)
        self._save_category_context(organization_context)
        self._go_to_link(self.MAIN_MENU__CASE_MENU, self.MAIN_MENU__EXPORT_CASE_LINK, 120)
        
        self._open_or_create_case(self.CASE_NAME_1)
        self._go_to_link(self.MAIN_MENU__CONTEXT_MENU, self.MAIN_MENU__CONTEXT_ORGANIZATION)
        self._save_category_context(organization_context)
        self._compute_similarity(True)
        self._assert_case_similar(self.CASE_NAME_2, 0.9167)
        
        self._logout()
        self._login(self.INITIAL__USER_NAME_3, self.INITIAL__PASSWORD_3)
        self._open_or_create_case(self.CASE_NAME_3)
        self._set_up_goal(lambda i: False)
        self._set_up_context(True)
        self._go_to_link(self.MAIN_MENU__STAKEHOLDERS_MENU, self.MAIN_MENU__STAKEHOLDERS_EDIT)
        self._save_stakeholders({})
        self._go_to_link(self.MAIN_MENU__CASE_MENU, self.MAIN_MENU__EXPORT_CASE_LINK, 120)
        
        # A case without information has a similarity of 0 with every case (including another case without information)
        self._open_or_create_case(self.CASE_NAME_4)
        self._set_up_goal(lambda i: False)
        self._set_up_context(True)
        self._go_to_link(self.MAIN_MENU__STAKEHOLDERS_MENU, self.MAIN_MENU__STAKEHOLDERS_EDIT)
        self._save_stakeholders({})
        self._compute_similarity(True, 0)
        self._assert_case_not_similar(self.CASE_NAME_1)
        self._assert_case_not_similar(self.CASE_NAME_2)
        self._assert_case_not_similar(self.CASE_NAME_3)
        
        # It is possible to retrieve a case where the user is not a stakeholder
        self._set_up_goal()
        self._compute_similarity(True, 0.2)
        self._assert_case_similar(self.CASE_NAME_1, 0.2807)
        
        
        
        
    def _set_up_goal(self, int_to_bool_func = lambda i: i%2 == 0):
        self._go_to_link(self.MAIN_MENU__GOAL_MENU, self.MAIN_MENU__GOAL_CUSTOMER_VALUE, 600)
        customer_goal = self._get_goal_category_information(self.GOAL_CATEGORY_CUSTOMER__PREFIX_ID, [1, 2, 3, 15, 16], int_to_bool_func)
        self._save_goal_category(customer_goal)
         
        self._go_to_link(self.MAIN_MENU__GOAL_MENU, self.MAIN_MENU__GOAL_FINANCIAL_VALUE)
        financial_goal = self._get_goal_category_information(self.GOAL_CATEGORY_FINANCIAL__PREFIX_ID, [4, 5], int_to_bool_func)
        self._save_goal_category(financial_goal)
         
        self._go_to_link(self.MAIN_MENU__GOAL_MENU, self.MAIN_MENU__GOAL_INTERNAL_BUSINESS_VALUE)
        internal_goal = self._get_goal_category_information(self.GOAL_CATEGORY_INTERNAL_BUSINESS__PREFIX_ID, range(6, 15), int_to_bool_func)
        self._save_goal_category(internal_goal)
         
        self._go_to_link(self.MAIN_MENU__GOAL_MENU, self.MAIN_MENU__GOAL_INNOVATION_AND_LEARNING_VALUE)
        innovation_goal = self._get_goal_category_information(self.GOAL_CATEGORY_INNOVATION_AND_LEARNING__PREFIX_ID, range(17, 23), int_to_bool_func)
        self._save_goal_category(innovation_goal)
                 
        self._go_to_link(self.MAIN_MENU__GOAL_MENU, self.MAIN_MENU__GOAL_MARKET_VALUE)
        market_goal = self._get_goal_category_information(self.GOAL_CATEGORY_MARKET__PREFIX_ID, range(5, 15), int_to_bool_func)
        self._save_goal_category(market_goal)
                
    def _get_goal_category_information(self, goal_category_prefix, id_iterable, int_to_bool_func = lambda i: i%2 == 0):
        return {goal_category_prefix + "{0:02d}".format(i) : int_to_bool_func(i) for i in id_iterable}
        
        
    def _set_up_context(self, empty_context = False):
        self._go_to_link(self.MAIN_MENU__CONTEXT_MENU, self.MAIN_MENU__CONTEXT_ORGANIZATION, 600)
        self._save_category_context(self._get_context_category_information(self.Context_category.ORGANIZATION, empty_context))
        self._go_to_link(self.MAIN_MENU__CONTEXT_MENU, self.MAIN_MENU__CONTEXT_PRODUCT)
        self._save_category_context(self._get_context_category_information(self.Context_category.PRODUCT, empty_context))
        self._go_to_link(self.MAIN_MENU__CONTEXT_MENU, self.MAIN_MENU__CONTEXT_STAKEHOLDER)
        self._save_category_context(self._get_context_category_information(self.Context_category.STAKEHOLDER, empty_context))
        self._go_to_link(self.MAIN_MENU__CONTEXT_MENU, self.MAIN_MENU__CONTEXT_METHOD)
        self._save_category_context(self._get_context_category_information(self.Context_category.METHOD, empty_context))
        self._go_to_link(self.MAIN_MENU__CONTEXT_MENU, self.MAIN_MENU__CONTEXT_BUSINESS)
        self._save_category_context(self._get_context_category_information(self.Context_category.BUSINESS, empty_context))
        
    def _get_context_category_information(self, context_category, empty_context = False):
        if context_category == self.Context_category.ORGANIZATION:
            result = {"O00_text": "",
                      "O01_multi_select": [],
                      "O02_single_select": self.CONTEXT_CATEGORY__DEFAULT_COMBO_BOX_OPTION,
                      "O03_single_select": "Medium",
                      "O04_text": "",
                      "O05.1_integer": 51,
                      "O05.2_integer": 0,
                      "O06_multi_select": ["CMMI"],
                      "O07_single_select": "Good capacity utilization",
                      "O08_single_select": "Medium",
                      "O09_multi_select": ["Bureaucratic", "Other"],
                      "O10_single_select": "Medium",
                      "O11_text": ""
                     }
        
        elif context_category == self.Context_category.PRODUCT:
            result = {"P00_text": "",
                      "P01_single_select": "High",
                      "P02_single_select": self.CONTEXT_CATEGORY__DEFAULT_COMBO_BOX_OPTION,
                      "P03_multi_select": ["Operating systems", "Servers", "Malware"],
                      "P04_single_select": self.CONTEXT_CATEGORY__DEFAULT_COMBO_BOX_OPTION,
                      "P05_single_select": "Medium",
                      "P06_text": "Answering the customers' needs",
                      "P07_multi_select": ["Usability"],
                      "P08_multi_select": [],
                      "P09_single_select": "Low",
                      "P10_multi_select": ["Ada", "Basic", "Perl"],
                      "P11_single_select": "Low",
                      "P12_text": "No other information available"
                     }
        
        elif context_category == self.Context_category.STAKEHOLDER:
            result = {"S00_text": "",
                      "S01_multi_select": ["Business (internal)", "Legal (external)"],
                      "S02_single_select": "High",
                      "S03_text": ""
                     }
        
        elif context_category == self.Context_category.METHOD:
            result = {"M00_text": "",
                      "M01_multi_select": ["Scrum"],
                      "M02_multi_select": [],
                      "M03_multi_select": ["Eclipse", "Delphi"],
                      "M04_single_select": "TRL 5",
                      "M05_integer": "75",
                      "M06_text": ""
                     }
        
        elif context_category == self.Context_category.BUSINESS:
            result = {"B00_text": "",
                      "B01_single_select": "Monopoly",
                      "B02_single_select": "Very",
                      "B03_text": "No competitors, a lot of suppliers",
                      "B04_single_select": "Somewhat",
                      "B05_text": "",
                      "B06_single_select": "Good",
                      "B07_single_select": "Stable contracts and agreements",
                      "B08_text": ""
                     }
        
        if empty_context:
            for key in result:
                if key.endswith(self.CONTEXT_CATEGORY__TEXT_ENTRY_SUFFIX):
                    result[key] = ""
                elif key.endswith(self.CONTEXT_CATEGORY__SINGLE_SELECT_ENTRY_SUFFIX):
                    result[key] = self.CONTEXT_CATEGORY__DEFAULT_COMBO_BOX_OPTION
                elif key.endswith(self.CONTEXT_CATEGORY__MULTI_SELECT_ENTRY_SUFFIX):
                    result[key] = []
                elif key.endswith(self.CONTEXT_CATEGORY__INTEGER_ENTRY_SUFFIX) or key.endswith(self.CONTEXT_CATEGORY__FLOAT_ENTRY_SUFFIX):
                    result[key] = 0
                else:
                    raise RuntimeError("Unknown suffix of key {0}.".format(key))
        return result
        
        
    def _set_up_stakeholder(self):
        self._go_to_link(self.MAIN_MENU__STAKEHOLDERS_MENU, self.MAIN_MENU__STAKEHOLDERS_EDIT, 600)
        self._save_stakeholders(self._get_stakeholder_information())
        
    def _get_stakeholder_information(self):
        return {self.INITIAL__USER_NAME_1: {self.STAKEHOLDER__ROLE_FUNCTION:["Leader", "Decider"],
                                            self.STAKEHOLDER__ROLE_LEVEL: ["Tactical"],
                                            self.STAKEHOLDER__ROLE_TITLE: ["Architect", "Integrator", "Test lead"],
                                            self.STAKEHOLDER__ROLE_TYPE: ["Asset user"]
                                           },
                self.INITIAL__USER_NAME_2: {self.STAKEHOLDER__ROLE_FUNCTION: ["Influencer", "Decider"],
                                            self.STAKEHOLDER__ROLE_LEVEL: [],
                                            self.STAKEHOLDER__ROLE_TITLE: ["Developer"],
                                            self.STAKEHOLDER__ROLE_TYPE: ["Asset supplier"]
                                           }
               }
        

    def _compute_similarity(self, export_case_to_kr=False, similarity_threshold=0.8, number_ratio_threshold=1.5):
        self._go_to_link(self.MAIN_MENU__CASE_MENU, self.MAIN_MENU__COMPUTE_SIMILARITY)
        self._send_key_in_field(self.COMPUTE_SIMILARITY__SIMILARITY_THRESHOLD_FIELD_NAME, similarity_threshold)
        self._send_key_in_field(self.COMPUTE_SIMILARITY__NUMBER_RATIO_THRESHOLD_FIELD_NAME, number_ratio_threshold)
        self._check_check_box(self.COMPUTE_SIMILARITY__EXPORT_CASE_CHECKBOX_NAME, export_case_to_kr)
        
        with self.wait_for_page_load(600):
            self.driver.find_element_by_tag_name("form").submit()
        
    
    def _assert_case_similar(self, case_title, similarity):
        self._assert_page(self.COMPUTED_SIMILARIRY__SUB_TITLE, True)
        
        similarity_string = self.SIMILARITY_VALUE_FORMATTER.format(similarity)
        self.assertIn("{0}: {1}".format(case_title, similarity_string), self.driver.page_source)
        
    def _assert_case_not_similar(self, case_title):
        self._assert_page(self.COMPUTED_SIMILARIRY__SUB_TITLE, True)
        self.assertNotIn(case_title, self.driver.page_source)
        
    
if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestSimilarity)
    unittest.TextTestRunner().run(suite)
    
    
    
    
    
    
    
    
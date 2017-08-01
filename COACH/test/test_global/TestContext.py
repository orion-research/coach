"""
Created on 27 juil. 2017

@author: francois
"""
import os
import sys
import unittest

sys.path.append(os.path.join(os.curdir, os.pardir, os.pardir, os.pardir))
from COACH.test.test_global.TestGlobal import TestGlobal

from selenium.webdriver.support.select import Select

class TestContext(TestGlobal):
    #edit_context_dialogue.html
    GENERAL_CONTEXT__SUB_TITLE = "Edit Context"
    GENERAL_CONTEXT__CONTEXT_GENERAL_ID = "General_text"
    GENERAL_CONTEXT__ORGANIZATION_GENERAL_ID = "O00_text"
    GENERAL_CONTEXT__PRODUCT_GENERAL_ID = "P00_text"
    GENERAL_CONTEXT__STAKEHOLDER_GENERAL_ID = "S00_text"
    GENERAL_CONTEXT__METHOD_GENERAL_ID = "M00_text"
    GENERAL_CONTEXT__BUSINESS_GENERAL_ID = "B00_text"
    GENERAL_CONTEXT__CONFIRMATION_MESSAGE = "Context information (general) saved."
    
    def test_context_model(self):
        """
        This method tests macro functionalities of the context model.
        
        It will test:
            - Store information into the general context and retrieve them
            - Store specific information in each category and retrieve them
            - Retrieve the general description of a category from a category view that was stored in the general view
            - Retrieve the general description of a category from the general view that was stored in a category view
            - Check that the "Unknown" values are not send to the database
            - Select 0 option on a multiple selection
            - Select 1 option on a multiple selection
            - Select more than 1 options on a multiple selection
            - Store a text entry without value
            - Store an integer entry without value
            - Change a value that was previously saved
            - Remove values from a multiple selection
        
        It will test only the organization category, as it is the same template to make all categories. 
        """
        # Store information into the general context and retrieve them
        self._go_to_link(self.MAIN_MENU__CONTEXT_MENU, self.MAIN_MENU__CONTEXT_GENERAL, 600)
        self._assert_general_context_page()
        self._save_general_context("General", "Organization", "Product", "Stakeholder", "Method", "Business")
        self.assertIn(self.GENERAL_CONTEXT__CONFIRMATION_MESSAGE, self.driver.page_source)
        self._go_to_link(self.MAIN_MENU__CONTEXT_MENU, self.MAIN_MENU__CONTEXT_GENERAL)
        self._assert_general_context_page(["General", "Organization", "Product", "Stakeholder", "Method", "Business"])
        
        # Retrieve the general description of a category from a category view that was stored in the general view
        # Store specific information in each category and retrieve them
        # Check that the "Unknown" values are not send to the database
        # Select 0 option on a multiple selection
        # Select 1 option on a multiple selection
        # Select more than 1 options on a multiple selection
        # Store a text entry without value
        # Store an integer entry without value
        # Change a value that was previously saved
        self._go_to_link(self.MAIN_MENU__CONTEXT_MENU, self.MAIN_MENU__CONTEXT_ORGANIZATION)
        self._assert_category_context_page(self.CONTEXT_CATEGORY_ORGANIZATION__SUB_TITLE, {"O00_text": "Organization"})
        category_information_dict = {"O00_text": "Organization category",
                                     "O01_multi_select": [],
                                     "O02_single_select": self.CONTEXT_CATEGORY__DEFAULT_COMBO_BOX_OPTION,
                                     "O03_single_select": "Medium",
                                     "O04_text": "O04 value",
                                     "O05.1_integer": 51,
                                     "O06_multi_select": ["CMMI"],
                                     "O07_single_select": "Good capacity utilization",
                                     "O08_single_select": "Medium",
                                     "O09_multi_select": ["Bureaucratic", "Other"],
                                     "O10_single_select": "Medium",
                                    }
        self._save_category_context(category_information_dict)
        self.assertIn(self.CONTEXT_CATEGORY_ORGANIZATION__CONFIRMATION_MESSAGE, self.driver.page_source)
        self._go_to_link(self.MAIN_MENU__CONTEXT_MENU, self.MAIN_MENU__CONTEXT_ORGANIZATION)
        # As unknown is not stored in the database, it becomes the default option
        category_information_dict["O02_single_select"] = self.CONTEXT_CATEGORY__DEFAULT_COMBO_BOX_OPTION
        self._assert_category_context_page(self.CONTEXT_CATEGORY_ORGANIZATION__SUB_TITLE, category_information_dict)
        
        # Retrieve the general description of a category from the general view that was stored in a category view
        self._go_to_link(self.MAIN_MENU__CONTEXT_MENU, self.MAIN_MENU__CONTEXT_GENERAL)
        self._assert_general_context_page(["General", "Organization category", "Product", "Stakeholder", "Method", "Business"])
        
        # Remove values from a multiple selection
        self._go_to_link(self.MAIN_MENU__CONTEXT_MENU, self.MAIN_MENU__CONTEXT_ORGANIZATION)
        self._assert_category_context_page(self.CONTEXT_CATEGORY_ORGANIZATION__SUB_TITLE, category_information_dict)
        category_information_dict["O02_single_select"] = "Low"
        category_information_dict["O09_multi_select"] = ["Virtual"]
        self._save_category_context(category_information_dict)
        self.assertIn(self.CONTEXT_CATEGORY_ORGANIZATION__CONFIRMATION_MESSAGE, self.driver.page_source)
        self._go_to_link(self.MAIN_MENU__CONTEXT_MENU, self.MAIN_MENU__CONTEXT_ORGANIZATION)
        self._assert_category_context_page(self.CONTEXT_CATEGORY_ORGANIZATION__SUB_TITLE, category_information_dict)


    def _save_general_context(self, general_description=None, organization_description=None, product_description=None, 
                              stakeholder_description=None, method_description=None, business_description=None):
        if general_description is not None:
            self._send_key_in_field(self.GENERAL_CONTEXT__CONTEXT_GENERAL_ID, general_description)
        if organization_description is not None:
            self._send_key_in_field(self.GENERAL_CONTEXT__ORGANIZATION_GENERAL_ID, organization_description)
        if product_description is not None:
            self._send_key_in_field(self.GENERAL_CONTEXT__PRODUCT_GENERAL_ID, product_description)
        if stakeholder_description is not None:
            self._send_key_in_field(self.GENERAL_CONTEXT__STAKEHOLDER_GENERAL_ID, stakeholder_description)
        if method_description is not None:
            self._send_key_in_field(self.GENERAL_CONTEXT__METHOD_GENERAL_ID, method_description)
        if business_description is not None:
            self._send_key_in_field(self.GENERAL_CONTEXT__BUSINESS_GENERAL_ID, business_description)
        
        with self.wait_for_page_load(30):
            self.driver.find_element_by_tag_name("form").submit()
            
            
    def _assert_general_context_page(self, expected_descriptions_list = ["", "", "", "", "", ""]):
        if len(expected_descriptions_list) != 6:
            raise RuntimeError("There must be exactly 6 elements in the description list, but {0} were found".format(len(expected_descriptions_list)))
        self._assert_page(self.GENERAL_CONTEXT__SUB_TITLE)
        
        actual_descriptions_list = [self.driver.find_element_by_name(self.GENERAL_CONTEXT__CONTEXT_GENERAL_ID).text,
                                    self.driver.find_element_by_name(self.GENERAL_CONTEXT__ORGANIZATION_GENERAL_ID).text,
                                    self.driver.find_element_by_name(self.GENERAL_CONTEXT__PRODUCT_GENERAL_ID).text,
                                    self.driver.find_element_by_name(self.GENERAL_CONTEXT__STAKEHOLDER_GENERAL_ID).text,
                                    self.driver.find_element_by_name(self.GENERAL_CONTEXT__METHOD_GENERAL_ID).text,
                                    self.driver.find_element_by_name(self.GENERAL_CONTEXT__BUSINESS_GENERAL_ID).text]
        self.assertListEqual(actual_descriptions_list, expected_descriptions_list)
        
        
    def _assert_category_context_page(self, page_sub_title, expected_information_dict={}):
        self._assert_page(page_sub_title)
        
        form_element = self.driver.find_element_by_tag_name("form")
        input_elements_list = form_element.find_elements_by_tag_name("input")
        select_elements_list = form_element.find_elements_by_tag_name("select")
        text_area_elements_list = form_element.find_elements_by_tag_name("textarea")
        
        for input_element in input_elements_list:
            element_name = input_element.get_attribute("name")
            element_value = input_element.get_attribute("value")
            self._assert_value_match_in_expected_dictionary(element_value, element_name, expected_information_dict)
            
        for text_area_element in text_area_elements_list:
            element_name = text_area_element.get_attribute("name")
            element_value = text_area_element.text
            self._assert_value_match_in_expected_dictionary(element_value, element_name, expected_information_dict)

        for select_element in select_elements_list:
            element_name = select_element.get_attribute("name")
            is_multiple_select = select_element.get_attribute("multiple")
            select_element = Select(select_element)
            
            if is_multiple_select:
                selected_option = [option.get_attribute("value") for option in select_element.all_selected_options]
                self._assert_value_match_in_expected_dictionary(selected_option, element_name, expected_information_dict)
            
            else:
                element_value = select_element.first_selected_option.text
                self._assert_value_match_in_expected_dictionary(element_value, element_name, expected_information_dict)
        
        self.assertEqual(len(expected_information_dict), 0)
            
    def _assert_value_match_in_expected_dictionary(self, value, key, expected_dictionary):
        if key in expected_dictionary:
            self.assertEqual(str(value), str(expected_dictionary[key]))
            del expected_dictionary[key]
            
            
if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestContext)
    unittest.TextTestRunner().run(suite)
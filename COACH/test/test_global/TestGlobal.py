"""
Created on 20 juin 2017

@author: francois
"""

# Set python import path to include COACH top directory
import os
import sys
import collections
sys.path.append(os.path.join(os.curdir, os.pardir, os.pardir, os.pardir))

from COACH.test.test_global.EstimationMethodValue import EstimationMethodValue

import unittest

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import UnexpectedTagNameException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.select import Select

from contextlib import contextmanager


#The name of each constant is <page name>__<constant name>

#Addresses
MAIN_PAGE_ADDRESS = "http://127.0.0.1:5000"

#initial_dialogue.html
INITIAL__PAGE_TITLE = "COACH"
INITIAL__USER_FIELD_NAME = "user_id"
INITIAL__PASSWORD_FIELD_NAME = "password"
INITIAL__USER_NAME = "valid"
INITIAL__PASSWORD = "valid"

#main_menu.html
MAIN_MENU__PAGE_TITLE = "COACH decision support system"

MAIN_MENU__CASE_MENU = "Case"
MAIN_MENU__OPEN_CASE_LINK = "Open case"
MAIN_MENU__NEW_CASE_LINK = "New case"
MAIN_MENU__CASE_STATUS_LINK = "Case status"
MAIN_MENU__CASE_DESCRIPTION_LINK = "Case description"
MAIN_MENU__EXPORT_CASE_LINK = "Export case to knowledge repository"
MAIN_MENU__CLOSE_CASE = "Close case"

MAIN_MENU__GOAL_MENU = "Goal"

MAIN_MENU__CONTEXT_MENU = "Context"
MAIN_MENU__CONTEXT_GENERAL = "General"
MAIN_MENU__CONTEXT_ORGANIZATION = "Organization"
MAIN_MENU__CONTEXT_PRODUCT = "Product"
MAIN_MENU__CONTEXT_STAKEHOLDER = "Stakeholder"
MAIN_MENU__CONTEXT_METHOD = "Development methods and technology"
MAIN_MENU__CONTEXT_BUSINESS = "Market and business"

MAIN_MENU__STAKEHOLDERS_MENU = "Stakeholders"

MAIN_MENU__ALTERNATIVES_MENU = "Alternatives"
MAIN_MENU__ADD_ALTERNATIVE_LINK = "Add"

MAIN_MENU__PROPERTIES_MENU = "Properties"
MAIN_MENU__PROPERTY_OVERVIEW_LINK = "Overview"
MAIN_MENU__PROPERTY_ESTIMATION_METHODS_LINK = "Estimation methods"

MAIN_MENU__TRADE_OFF_MENU = "Trade-off"

#open_case_dialogue.html
OPEN_CASE__SUB_TITLE = "Select a case to work on"

#create_case_dialogue.html
CREATE_CASE__SUB_TITLE = "Create new decision case"
CREATE_CASE__TITLE_FIELD_NAME = "title"
CREATE_CASE__DESCRIPTION_FIELD_NAME = "description"

#case_status_dialogue.html
CASE_STATUS__SUB_TITLE = "Case status"

#close_case_dialogue.html
CLOSE_CASE__SUB_TITLE = "Close case"
CLOSE_CASE__EXPORT_TO_KR_CHECKBOX_NAME = "export_to_kr_checkbox"
CLOSE_CASE__SELECTED_ALTERNATIVE_NAME = "selected_alternative"
CLOSE_CASE__NONE_ALTERNATIVE = "None"
CLOSE_CASE__CONFIRMATION_MESSAGE = "Case closed"

#add_alternative_dialogue.html
ADD_ALTERNATIVE__SUB_TITLE = "Add new decision alternative"
ADD_ALTERNATIVE__TITLE_FIELD_NAME = "title"
ADD_ALTERNATIVE__DESCRIPTION_FIELD_NAME = "description"
ADD_ALTERNATIVE__USAGE_FIELD_NAME = "asset_usage"
ADD_ALTERNATIVE__ORIGIN_FIELD_NAME = "asset_origin"
ADD_ALTERNATIVE__TYPE_FIELD_NAME = "asset_type"
ADD_ALTERNATIVE__CONFIRMATION_MESSAGE = "New alternative added!"

#properties_overview_dialogue.html
PROPERTY_OVERVIEW__SUB_TITLE = "Properties"

#properties_estimation_methods_dialogue.html
PROPERTY_ESTIMATION_METHOD__SUB_TITLE = "Estimation methods"
PROPERTY_ESTIMATION_METHOD__ALTERNATIVE_SELECT_NAME = "alternative_name"
PROPERTY_ESTIMATION_METHOD__PROPERTY_SELECT_NAME = "property_name"
PROPERTY_ESTIMATION_METHOD__ESTIMATION_METHOD_SELECT_NAME = "estimation_method_name"
PROPERTY_ESTIMATION_METHOD__SUBMIT_COMPONENT_NAME = "submit_component"
PROPERTY_ESTIMATION_METHOD__USED_PROPERTIES_LIST_ID = "used_properties"
PROPERTY_ESTIMATION_METHOD__PARAMETERS_LIST_ID = "used_parameters"
PROPERTY_ESTIMATION_METHOD__USED_PROPERTIES_SELECT_SUFFIX = "_selected_estimation_method"
PROPERTY_ESTIMATION_METHOD__USED_PROPERTIES_VALUE_SUFFIX = "_property_value"
PROPERTY_ESTIMATION_METHOD__PARAMETER_NAME_SUFFIX = "_parameter"
PROPERTY_ESTIMATION_METHOD__COMPUTE_BUTTON_VALUE = "Compute"
PROPERTY_ESTIMATION_METHOD__DELETE_BUTTON_VALUE = "Delete"
PROPERTY_ESTIMATION_METHOD__GOTO_BUTTON_SUFFIX = "_goto_button"
PROPERTY_ESTIMATION_METHOD__NO_COMPUTE_VALUE_MESSAGE = "This estimation has not been computed yet"
PROPERTY_ESTIMATION_METHOD__COMPUTE_VALUE_MESSAGE = "Current value is "
PROPERTY_ESTIMATION_METHOD__NOT_COMPUTED_VALUE = "---"
PROPERTY_ESTIMATION_METHOD__USED_PROPERTY_OUT_OF_DATE_MESSAGE = "/!\ This value is out-of-date"
PROPERTY_ESTIMATION_METHOD__ESTIMATION_OUT_OF_DATE_MESSAGE = "/!\ The current value is out-of-date"

#edit_context_dialogue.html
GENERAL_CONTEXT__SUB_TITLE = "Edit Context"
GENERAL_CONTEXT__CONTEXT_GENERAL_ID = "General_text"
GENERAL_CONTEXT__ORGANIZATION_GENERAL_ID = "O00_text"
GENERAL_CONTEXT__PRODUCT_GENERAL_ID = "P00_text"
GENERAL_CONTEXT__STAKEHOLDER_GENERAL_ID = "S00_text"
GENERAL_CONTEXT__METHOD_GENERAL_ID = "M00_text"
GENERAL_CONTEXT__BUSINESS_GENERAL_ID = "B00_text"
GENERAL_CONTEXT__CONFIRMATION_MESSAGE = "Context information (general) saved."

#context_category_dialogue.html
CONTEXT_CATEGORY__DEFAULT_COMBO_BOX_OPTION = "Unknown"
CONTEXT_CATEGORY_ORGANIZATION__SUB_TITLE = "Context details - Organization"
CONTEXT_CATEGORY_ORGANIZATION__CONFIRMATION_MESSAGE = "Context information (organization) saved."


class TestGlobal (unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        super(TestGlobal, cls).setUpClass()
        cls.driver = webdriver.Firefox()
        
    @classmethod
    def tearDownClass(cls):
        super(TestGlobal, cls).tearDownClass()
        cls.driver.close()
        
    def setUp(self):
        self.driver.get(MAIN_PAGE_ADDRESS)
        self._assert_initial_page()
        self._login()
        self._assert_unactive_case()
        self._go_to_link(MAIN_MENU__CASE_MENU, MAIN_MENU__NEW_CASE_LINK)
        self._assert_page(CREATE_CASE__SUB_TITLE, False)
        self._create_case("case")
        self._assert_page(CASE_STATUS__SUB_TITLE)
        
        self.alternatives_name_list = []
        self.estimation_value_list = []
        
    def tearDown(self):
        self._go_to_link(MAIN_MENU__CASE_MENU, MAIN_MENU__CLOSE_CASE)
        export_to_kr_checkbox = self.driver.find_element_by_name(CLOSE_CASE__EXPORT_TO_KR_CHECKBOX_NAME)
        if export_to_kr_checkbox.is_selected():
            export_to_kr_checkbox.click()
        
        self._select_combo_box(CLOSE_CASE__SELECTED_ALTERNATIVE_NAME, CLOSE_CASE__NONE_ALTERNATIVE)
        
        with self.wait_for_page_load():
            export_to_kr_checkbox.submit()
        self.assertIn(CLOSE_CASE__CONFIRMATION_MESSAGE, self.driver.page_source)
        
        
    @contextmanager
    def wait_for_page_load(self, timeout=5):
        """
        Utility method to wait until a page is loaded. It will not work if the html does not change (angular application for example)
        More information on http://www.obeythetestinggoat.com/how-to-get-selenium-to-wait-for-page-load-after-a-click.html
        It is used as follows:
        
        with wait_for_page_load():
            #action to change page
        #action on the new page
        """
        old_page = self.driver.find_element_by_tag_name('html')
        yield
        WebDriverWait(self.driver, timeout).until(EC.staleness_of(old_page))
        
    def test_property_estimation_method(self):
        """
        This method tests macro functionalities on the property model. 
        
        It will test:
            - Creation of an alternative
            - Estimation computed for different alternatives
            - Overview page without any estimation being computed
            - Shortcut with a click on a cell of the overview page
            - Compute an estimation with parameters
            - Compute an estimation with used properties
            - Message before a value is computed
            - Up-to-date is set to False when a used property is re-computed
            - Delete a property
            - Up-to-date is set to False when a used property is deleted
            - When up-to-date is False, the overview background is yellow
            - When up-to-date is False, a warning message is displayed before the value of the current estimation
            - When up-to-date is False, a warning message is displayed before the value of the used estimation
            - Shortcut with the goto button
            - Selectable estimation method are those for the selected property
            - Selectable estimation method for a used property are those for this property
            - If a used estimation has not been computed yet, the compute button is disable
            - If all used estimations have been computed, the compute button is enable
            - If an estimation has not been computed yet, the delete button is disable
            - If an estimation has been computed, the delete button is enable
            - When up-to-date is False, it becomes True once the estimation is re computed
            - Selected estimation method for used properties is the one used for the last computation
            - Parameters's value are the ones used for the last computation
        """
        # Creation of an alternative
        self._go_to_link(MAIN_MENU__ALTERNATIVES_MENU, MAIN_MENU__ADD_ALTERNATIVE_LINK, 600)
        self._add_alternative("Alt 1")
        self.assertIn(ADD_ALTERNATIVE__CONFIRMATION_MESSAGE, self.driver.page_source)
        self._go_to_link(MAIN_MENU__ALTERNATIVES_MENU, MAIN_MENU__ADD_ALTERNATIVE_LINK)
        self._add_alternative("Alt 2")
        self.assertIn(ADD_ALTERNATIVE__CONFIRMATION_MESSAGE, self.driver.page_source)
        
        # Overview page without any estimation being computed
        # Shortcut with a click on a cell of the overview page
        # Message before a value is computed
        # Compute an estimation with parameters
        # Selectable estimation method are those for the selected property
        # If an estimation has not been computed yet, the delete button is disable
        # If an estimation has been computed, the delete button is enable
        estimation = ("Alt 1", "Development effort", "Expert estimate float")
        self._go_to_link(MAIN_MENU__PROPERTIES_MENU, MAIN_MENU__PROPERTY_OVERVIEW_LINK, 600)
        self._assert_property_overview_page()
        self._click_on_property_overview_shortcut(estimation)
        self._assert_property_estimation_method_page(estimation)
        self._assert_compute_value(None)
        self._compute({"estimation": 5})
        self.estimation_value_list.append((*estimation, 5.0))
        self._assert_compute_value(5)
        self._go_to_link(MAIN_MENU__PROPERTIES_MENU, MAIN_MENU__PROPERTY_OVERVIEW_LINK, 30)
        self._assert_property_overview_page()
  
        # Compute an estimation with used properties
        # Selectable estimation method for a used property are those for this property
        # If all used estimations have been computed, the compute button is enable
        estimation = ("Alt 1", "Cost", "Cost estimation")
        self._go_to_link(MAIN_MENU__PROPERTIES_MENU, MAIN_MENU__PROPERTY_ESTIMATION_METHODS_LINK)
        self._assert_property_estimation_method_page()
        self._select_estimation(estimation)
        self._assert_compute_value(None)
        self._assert_property_estimation_method_page(estimation)
        self._compute({"Salary": 10}, {"Development effort": "Expert estimate float"})
        self.estimation_value_list.append((*estimation, 50.0))
        self._assert_compute_value(50)
        self._go_to_link(MAIN_MENU__PROPERTIES_MENU, MAIN_MENU__PROPERTY_OVERVIEW_LINK)
        self._assert_property_overview_page()
        
        # Up-to-date is set to False when a used property is re-computed
        # When up-to-date is False, the overview background is yellow
        # When up-to-date is False, a warning message is displayed before the value of the current estimation
        # Parameters's value are the ones used for the last computation
        estimation = ("Alt 1", "Development effort", "Expert estimate float")
        self._click_on_property_overview_shortcut(estimation)
        self._assert_property_estimation_method_page(estimation, {"estimation": 5})
        self._assert_compute_value(5)
        self._compute()
        self._assert_property_estimation_method_page(estimation, {"estimation": 5})
        self._assert_compute_value(5)
        poped_estimation = self.estimation_value_list.pop(-1)
        self.estimation_value_list.append((*poped_estimation, False))
        self._go_to_link(MAIN_MENU__PROPERTIES_MENU, MAIN_MENU__PROPERTY_OVERVIEW_LINK)
        self._assert_property_overview_page()
        
        # When up-to-date is False, it becomes True once the estimation is re computed
        # Selected estimation method for used properties is the one used for the last computation
        estimation = ("Alt 1", "Cost", "Cost estimation")
        self._click_on_property_overview_shortcut(estimation)
        self._assert_property_estimation_method_page(estimation, {"Salary": 10}, {"Development effort": ("Expert estimate float", True)}, False)
        self._assert_compute_value(50)
        self._compute()
        self._assert_compute_value(50)
        self._assert_property_estimation_method_page(estimation, {"Salary": 10}, {"Development effort": ("Expert estimate float", True)}, True)
        self.estimation_value_list.pop(-1)
        self.estimation_value_list.append((*estimation, 50.0))
        self._go_to_link(MAIN_MENU__PROPERTIES_MENU, MAIN_MENU__PROPERTY_OVERVIEW_LINK)
        self._assert_property_overview_page()
        
        # If a used estimation has not been computed yet, the compute button is disable
        estimation = ("Alt 2", "Development effort", "Basic COCOMO")
        self._click_on_property_overview_shortcut(estimation)
        self._assert_property_estimation_method_page(estimation)
        
        # Shortcut with the goto button
        # Estimation computed for different alternatives
        estimation = ("Alt 2", "KLOC", "Expert estimate float")
        self._click_on_goto_button("KLOC", "Expert estimate float")
        self._assert_property_estimation_method_page(estimation)
        self._assert_compute_value(None)
        self._compute({"estimation": 5})
        self.estimation_value_list.append((*estimation, 5.0))
        self._assert_property_estimation_method_page(estimation, {"estimation": 5})
        self._assert_compute_value(5)
        self._go_to_link(MAIN_MENU__PROPERTIES_MENU, MAIN_MENU__PROPERTY_OVERVIEW_LINK)
        self._assert_property_overview_page()
        
        estimation = ("Alt 2", "Development effort", "Basic COCOMO")
        self._click_on_property_overview_shortcut(estimation)
        self._assert_property_estimation_method_page(estimation)
        self._assert_compute_value(None)
        self._compute({"developmentMode": "Semi-detached"}, {"KLOC": "Expert estimate float"})
        self.estimation_value_list.append((*estimation, 18.1957))
        self._assert_property_estimation_method_page(estimation, {"developmentMode": "Semi-detached"}, {"KLOC": ("Expert estimate float", True)})
        self._assert_compute_value(18.1957)
        self._go_to_link(MAIN_MENU__PROPERTIES_MENU, MAIN_MENU__PROPERTY_OVERVIEW_LINK)
        self._assert_property_overview_page()
        
        estimation = ("Alt 2", "KLOC", "Expert estimate float")
        self._click_on_property_overview_shortcut(estimation)
        self._assert_property_estimation_method_page(estimation, {"estimation": 5})
        self._assert_compute_value(5)
        self._compute()
        poped_estimation = self.estimation_value_list.pop(-1)
        self.estimation_value_list.append((*poped_estimation, False))
        self._assert_property_estimation_method_page(estimation, {"estimation": 5})
        self._assert_compute_value(5)
        self._go_to_link(MAIN_MENU__PROPERTIES_MENU, MAIN_MENU__PROPERTY_OVERVIEW_LINK)
        self._assert_property_overview_page()
        
        # When up-to-date is False, a warning message is displayed before the value of the used estimation
        estimation = ("Alt 2", "Cost", "Cost estimation")
        self._click_on_property_overview_shortcut(estimation)
        self._assert_property_estimation_method_page(estimation)
        self._assert_compute_value(None)
        self._compute({"Salary": 10}, {"Development effort": "Basic COCOMO"})
        self.estimation_value_list.append((*estimation, 181.9565))
        self._assert_property_estimation_method_page(estimation, {"Salary": 10}, {"Development effort": ("Basic COCOMO", False)})
        self._assert_compute_value(181.9565)
        self._go_to_link(MAIN_MENU__PROPERTIES_MENU, MAIN_MENU__PROPERTY_OVERVIEW_LINK)
        self._assert_property_overview_page()
        
        # Delete a property
        # Up-to-date is set to False when a used property is deleted
        estimation = ("Alt 2", "Development effort", "Basic COCOMO")
        self._click_on_property_overview_shortcut(estimation)
        self._assert_property_estimation_method_page(estimation, {"developmentMode": "Semi-detached"}, {"KLOC": ("Expert estimate float", True)}, False)
        self._assert_compute_value(18.1957)
        self._delete()
        self.estimation_value_list.pop(-2)
        # The property is still linked to the alternative in the database, so "---" will appear in the overview.
        self.estimation_value_list.append((*estimation, PROPERTY_ESTIMATION_METHOD__NOT_COMPUTED_VALUE))
        poped_estimation = self.estimation_value_list.pop(-2)
        self.estimation_value_list.append((*poped_estimation, False))
        self._assert_property_estimation_method_page(estimation)
        self._assert_compute_value(None)
        self._go_to_link(MAIN_MENU__PROPERTIES_MENU, MAIN_MENU__PROPERTY_OVERVIEW_LINK)
        self._assert_property_overview_page()
        
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
        self._go_to_link(MAIN_MENU__CONTEXT_MENU, MAIN_MENU__CONTEXT_GENERAL, 600)
        self._assert_general_context_page()
        self._save_general_context("General", "Organization", "Product", "Stakeholder", "Method", "Business")
        self.assertIn(GENERAL_CONTEXT__CONFIRMATION_MESSAGE, self.driver.page_source)
        self._go_to_link(MAIN_MENU__CONTEXT_MENU, MAIN_MENU__CONTEXT_GENERAL)
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
        self._go_to_link(MAIN_MENU__CONTEXT_MENU, MAIN_MENU__CONTEXT_ORGANIZATION)
        self._assert_category_context_page(CONTEXT_CATEGORY_ORGANIZATION__SUB_TITLE, {"O00_text": "Organization"})
        category_information_dict = {"O00_text": "Organization category",
                                     "O01_multi_select": [],
                                     "O02_single_select": "Unknown",
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
        self.assertIn(CONTEXT_CATEGORY_ORGANIZATION__CONFIRMATION_MESSAGE, self.driver.page_source)
        self._go_to_link(MAIN_MENU__CONTEXT_MENU, MAIN_MENU__CONTEXT_ORGANIZATION)
        # As unknown is not stored in the database, it becomes the default option
        category_information_dict["O02_single_select"] = CONTEXT_CATEGORY__DEFAULT_COMBO_BOX_OPTION
        self._assert_category_context_page(CONTEXT_CATEGORY_ORGANIZATION__SUB_TITLE, category_information_dict)
        
        # Retrieve the general description of a category from the general view that was stored in a category view
        self._go_to_link(MAIN_MENU__CONTEXT_MENU, MAIN_MENU__CONTEXT_GENERAL)
        self._assert_general_context_page(["General", "Organization category", "Product", "Stakeholder", "Method", "Business"])
        
        # Remove values from a multiple selection
        self._go_to_link(MAIN_MENU__CONTEXT_MENU, MAIN_MENU__CONTEXT_ORGANIZATION)
        self._assert_category_context_page(CONTEXT_CATEGORY_ORGANIZATION__SUB_TITLE, category_information_dict)
        category_information_dict["O02_single_select"] = "Low"
        category_information_dict["O09_multi_select"] = ["Virtual"]
        self._save_category_context(category_information_dict)
        self.assertIn(CONTEXT_CATEGORY_ORGANIZATION__CONFIRMATION_MESSAGE, self.driver.page_source)
        self._go_to_link(MAIN_MENU__CONTEXT_MENU, MAIN_MENU__CONTEXT_ORGANIZATION)
        self._assert_category_context_page(CONTEXT_CATEGORY_ORGANIZATION__SUB_TITLE, category_information_dict)
        
        
        
    def _select_combo_box(self, combo_box_name, option_name = None, page_load = False, timeout = 5, option_name_list = None):
        if (option_name is None and option_name_list is None) or (option_name is not None and option_name_list is not None):
            raise RuntimeError("Exactly 1 among option_name and option_name_list must be None")
        
        select_element = self.driver.find_element_by_name(combo_box_name)
        is_multiple = select_element.get_attribute("multiple")
        select_element = Select(self.driver.find_element_by_name(combo_box_name))
        if option_name_list is not None and not is_multiple:
            raise RuntimeError("Can't select multiple value in a single select")
        
        if option_name is not None:
            # If the value is already selected, there is nothing to be done
            if select_element.first_selected_option.text == option_name:
                return
            option_name_list = [option_name]
        else:
            select_element.deselect_all()
            
        for option_name in option_name_list:
            if page_load:
                with self.wait_for_page_load(timeout):
                    select_element.select_by_visible_text(option_name)
            else:
                select_element.select_by_visible_text(option_name)

    def _send_key_in_text_field(self, text_field_name, message, clear=True):
        text_field_element = self.driver.find_element_by_name(text_field_name)
        if clear:
            text_field_element.clear()
        text_field_element.send_keys(message)
    
    
    def _login(self):
        self._send_key_in_text_field(INITIAL__USER_FIELD_NAME, INITIAL__USER_NAME)
        self._send_key_in_text_field(INITIAL__PASSWORD_FIELD_NAME, INITIAL__PASSWORD)
        with self.wait_for_page_load():
            self.driver.find_element_by_tag_name("form").submit()
        
    def _go_to_link(self, menu_name, link_name, timeout = 5):
        menu = self.driver.find_element_by_link_text(menu_name)
        # The mouse need to move over the menu element to display the sub-menu. 
        # The 1 pixel move is useful when the mouse is already on the element, as the first action won't move the mouse.
        hover = ActionChains(self.driver).move_to_element(menu)
        hover.move_by_offset(1, 1)
        hover.perform()
        
        WebDriverWait(self.driver, 1).until(EC.visibility_of_element_located((By.LINK_TEXT, link_name)))
        link = self.driver.find_element_by_link_text(link_name)
        with self.wait_for_page_load(timeout):
            link.click()
    
    def _open_case(self, case_name):
        case_to_open_link = self.driver.find_element_by_link_text(case_name)
        with self.wait_for_page_load():
            case_to_open_link.click()
        
    def _create_case(self, case_name, case_description = "desc"):
        self._send_key_in_text_field(CREATE_CASE__TITLE_FIELD_NAME, case_name)
        self._send_key_in_text_field(CREATE_CASE__DESCRIPTION_FIELD_NAME, case_description)
        with self.wait_for_page_load():
            self.driver.find_element_by_tag_name("form").submit()
        
    def _add_alternative(self, alternative_name, alternative_description = "desc", alternative_usage="Unknown",
                         alternative_origin="Unknown", alternative_type_list=[]):
        self.alternatives_name_list.append(alternative_name)
        
        self._send_key_in_text_field(ADD_ALTERNATIVE__TITLE_FIELD_NAME, alternative_name)
        self._send_key_in_text_field(ADD_ALTERNATIVE__DESCRIPTION_FIELD_NAME, alternative_description)
        self._select_combo_box(ADD_ALTERNATIVE__USAGE_FIELD_NAME, alternative_usage)
        self._select_combo_box(ADD_ALTERNATIVE__ORIGIN_FIELD_NAME, alternative_origin)
        
        type_field = self.driver.find_element_by_name(ADD_ALTERNATIVE__TYPE_FIELD_NAME)
        parameter_element = Select(type_field)
        for alternative_type in alternative_type_list:
            parameter_element.select_by_visible_text(alternative_type)
        
        with self.wait_for_page_load():
            type_field.submit()
        
    def _click_on_property_overview_shortcut(self, estimation):
        (alternative_name, property_name, estimation_method_name) = estimation
        
        if "&" in alternative_name or "&" in property_name or "&" in estimation_method_name:
            raise NotImplementedError("Name containing '&' are not implemented yet")
        
        table_element = self.driver.find_element_by_tag_name("table")
        links_element = table_element.find_elements_by_tag_name("a")
        for link in links_element:
            link_text = link.get_attribute("href").replace("%20", " ")
            link_split_text = link_text.split("&")
            link_alternative_name = link_split_text[1].split("=")[1].strip()
            link_property_name = link_split_text[2].split("=")[1].strip()
            link_estimation_method_name = link_split_text[3].split("=")[1].strip()
            
            if (alternative_name == link_alternative_name and property_name == link_property_name and
                    estimation_method_name == link_estimation_method_name):
                with self.wait_for_page_load():
                    link.find_element_by_tag_name("div").click()
                return
            
        raise RuntimeError("The link ({0}, {1}, {2}) should have been clicked.".format(alternative_name, property_name, estimation_method_name))
        
    def _compute(self, parameters_dict = {}, used_properties_dict = {}):
        # The page is refresh each time a used property is selected: it must be done before keying in parameters 
        for used_property_name in used_properties_dict:
            self._select_combo_box(used_property_name + "_selected_estimation_method", used_properties_dict[used_property_name], True)

        for parameter_name in parameters_dict:
            try:
                self._select_combo_box(parameter_name + "_parameter", parameters_dict[parameter_name])
            except UnexpectedTagNameException: #Throw when trying to create a Select without a select element
                self._send_key_in_text_field(parameter_name + "_parameter", parameters_dict[parameter_name])
        
        compute_button = self._find_submit_component(PROPERTY_ESTIMATION_METHOD__COMPUTE_BUTTON_VALUE)
        with self.wait_for_page_load():
            compute_button.click()
    
    def _delete(self):
        delete_button = self._find_submit_component(PROPERTY_ESTIMATION_METHOD__DELETE_BUTTON_VALUE)
        with self.wait_for_page_load():
            delete_button.click()

    def _click_on_goto_button(self, property_name, estimation_method_name):
        self._select_combo_box(property_name + PROPERTY_ESTIMATION_METHOD__USED_PROPERTIES_SELECT_SUFFIX, estimation_method_name, True)
        goto_button = self._find_submit_component(property_name + PROPERTY_ESTIMATION_METHOD__GOTO_BUTTON_SUFFIX)
        with self.wait_for_page_load():
            goto_button.click()
    
    def _find_submit_component(self, component_value):
        submit_elements = self.driver.find_elements_by_name(PROPERTY_ESTIMATION_METHOD__SUBMIT_COMPONENT_NAME)
        for submit_element in submit_elements:
            if submit_element.get_attribute("value") == component_value:
                return submit_element
    
    def _select_estimation(self, estimation = (None, None, None)):
        (alternative_name, property_name, estimation_method_name) = estimation
        
        if alternative_name is not None:
            self._select_combo_box(PROPERTY_ESTIMATION_METHOD__ALTERNATIVE_SELECT_NAME, alternative_name, True)
        if property_name is not None:
            self._select_combo_box(PROPERTY_ESTIMATION_METHOD__PROPERTY_SELECT_NAME, property_name, True)
        if estimation_method_name is not None:
            self._select_combo_box(PROPERTY_ESTIMATION_METHOD__ESTIMATION_METHOD_SELECT_NAME, estimation_method_name, True)
            

    def _save_general_context(self, general_description=None, organization_description=None, product_description=None, 
                              stakeholder_description=None, method_description=None, business_description=None):
        if general_description is not None:
            self._send_key_in_text_field(GENERAL_CONTEXT__CONTEXT_GENERAL_ID, general_description)
        if organization_description is not None:
            self._send_key_in_text_field(GENERAL_CONTEXT__ORGANIZATION_GENERAL_ID, organization_description)
        if product_description is not None:
            self._send_key_in_text_field(GENERAL_CONTEXT__PRODUCT_GENERAL_ID, product_description)
        if stakeholder_description is not None:
            self._send_key_in_text_field(GENERAL_CONTEXT__STAKEHOLDER_GENERAL_ID, stakeholder_description)
        if method_description is not None:
            self._send_key_in_text_field(GENERAL_CONTEXT__METHOD_GENERAL_ID, method_description)
        if business_description is not None:
            self._send_key_in_text_field(GENERAL_CONTEXT__BUSINESS_GENERAL_ID, business_description)
        
        with self.wait_for_page_load(30):
            self.driver.find_element_by_tag_name("form").submit()
            
    def _save_category_context(self, entries_value_dict):
        for entry_name in entries_value_dict:
            entry_value = entries_value_dict[entry_name]
            try:
                if (isinstance(entry_value, collections.Iterable) and not isinstance(entry_value, str)):
                    self._select_combo_box(entry_name, option_name_list=entry_value)
                else:
                    self._select_combo_box(entry_name, entry_value)
            except UnexpectedTagNameException: #Throw when trying to create a Select without a select element
                self._send_key_in_text_field(entry_name, entry_value)
                
        with self.wait_for_page_load(30):
            self.driver.find_element_by_tag_name("form").submit()
        
    def _assert_initial_page(self):
        self.assertIn(INITIAL__PAGE_TITLE, self.driver.title)
        
    def _assert_unactive_case(self):
        try:
            self.driver.find_element_by_link_text(MAIN_MENU__CASE_MENU) 
            self.driver.find_element_by_link_text(MAIN_MENU__OPEN_CASE_LINK)
            self.driver.find_element_by_link_text(MAIN_MENU__NEW_CASE_LINK)
            self.assertRaises(NoSuchElementException, self.driver.find_element_by_link_text, MAIN_MENU__CASE_STATUS_LINK)
            self.assertRaises(NoSuchElementException, self.driver.find_element_by_link_text, MAIN_MENU__CASE_DESCRIPTION_LINK)
            self.assertRaises(NoSuchElementException, self.driver.find_element_by_link_text, MAIN_MENU__EXPORT_CASE_LINK)
            self.assertRaises(NoSuchElementException, self.driver.find_element_by_link_text, MAIN_MENU__GOAL_MENU)
            self.assertRaises(NoSuchElementException, self.driver.find_element_by_link_text, MAIN_MENU__STAKEHOLDERS_MENU)
            self.assertRaises(NoSuchElementException, self.driver.find_element_by_link_text, MAIN_MENU__ALTERNATIVES_MENU)
            self.assertRaises(NoSuchElementException, self.driver.find_element_by_link_text, MAIN_MENU__PROPERTIES_MENU)
            self.assertRaises(NoSuchElementException, self.driver.find_element_by_link_text, MAIN_MENU__TRADE_OFF_MENU)
        except NoSuchElementException as e:
            self.fail(str(e))
    
    def _assert_active_case(self):
        try:
            self.driver.find_element_by_link_text(MAIN_MENU__CASE_MENU)
            self.driver.find_element_by_link_text(MAIN_MENU__OPEN_CASE_LINK)
            self.driver.find_element_by_link_text(MAIN_MENU__NEW_CASE_LINK)
            self.driver.find_element_by_link_text(MAIN_MENU__CASE_STATUS_LINK)
            self.driver.find_element_by_link_text(MAIN_MENU__CASE_DESCRIPTION_LINK)
            self.driver.find_element_by_link_text(MAIN_MENU__EXPORT_CASE_LINK)
            self.driver.find_element_by_link_text(MAIN_MENU__GOAL_MENU)
            self.driver.find_element_by_link_text(MAIN_MENU__STAKEHOLDERS_MENU)
            self.driver.find_element_by_link_text(MAIN_MENU__ALTERNATIVES_MENU)
            self.driver.find_element_by_link_text(MAIN_MENU__PROPERTIES_MENU)
            self.driver.find_element_by_link_text(MAIN_MENU__TRADE_OFF_MENU)
        except NoSuchElementException as e:
            self.fail(str(e))


    def _assert_page(self, page_sub_title, is_case_active = True):
        subTitle = self.driver.find_element_by_tag_name("h2")
        self.assertEqual(subTitle.text, page_sub_title)
        if is_case_active:
            self._assert_active_case()
        else:
            self._assert_unactive_case()
    
    def _assert_property_overview_page(self):
        self._assert_page(PROPERTY_OVERVIEW__SUB_TITLE)
        actual_estimation_method_value = EstimationMethodValue.build_from_web_page(self.driver)
        expected_estimation_method_value = EstimationMethodValue.build_expected_result(self.alternatives_name_list, self.estimation_value_list)
        self.assertEqual(actual_estimation_method_value, expected_estimation_method_value)
        
    def _assert_property_estimation_method_page(self, estimation = (None, None, None), parameters_value = {}, used_properties_estimation_method = {}, 
                                                up_to_date = True):
        (alternative_name, property_name, estimation_method_name) = estimation
            
        self._assert_page(PROPERTY_ESTIMATION_METHOD__SUB_TITLE)
        alternative_select = Select(self.driver.find_element_by_name(PROPERTY_ESTIMATION_METHOD__ALTERNATIVE_SELECT_NAME))
        property_select = Select(self.driver.find_element_by_name(PROPERTY_ESTIMATION_METHOD__PROPERTY_SELECT_NAME))
        estimation_method_select = Select(self.driver.find_element_by_name(PROPERTY_ESTIMATION_METHOD__ESTIMATION_METHOD_SELECT_NAME))
        
        # Assert selected alternative, property, estimation method
        if alternative_name is not None:
            self.assertEqual(alternative_name, alternative_select.first_selected_option.text)
        if property_name is not None:
            self.assertEqual(property_name, property_select.first_selected_option.text)
        if estimation_method_name is not None:
            self.assertEqual(estimation_method_name, estimation_method_select.first_selected_option.text)
        
        # Assert list of possible alternatives, properties, estimation methods
        self.assertEqual(set(self.alternatives_name_list), {option.text for option in alternative_select.options})
        
        properties_name_list = EstimationMethodValue.get_expected_properties_name_list()
        self.assertEqual(set(properties_name_list), {option.text for option in property_select.options})
        
        estimation_methods_name_list = EstimationMethodValue.get_expected_estimation_methods_name_list(property_select.first_selected_option.text)
        self.assertEqual(set(estimation_methods_name_list), {option.text for option in estimation_method_select.options})
        
        self._assert_used_properties(used_properties_estimation_method)
        self._assert_parameters(parameters_value)
        self.assertEqual(up_to_date, PROPERTY_ESTIMATION_METHOD__ESTIMATION_OUT_OF_DATE_MESSAGE not in self.driver.page_source)
        
    def _assert_used_properties(self, used_properties_estimation_method):
        is_compute_button_enable = True
        try:
            used_properties_list_element = self.driver.find_element_by_id(PROPERTY_ESTIMATION_METHOD__USED_PROPERTIES_LIST_ID)
            used_properties_list_item_list = used_properties_list_element.find_elements_by_tag_name("li")
        except NoSuchElementException:
            used_properties_list_item_list = []
            
        for list_element in used_properties_list_item_list:
            select_used_property = list_element.find_element_by_tag_name("select")
            property_name = select_used_property.get_attribute("name")[:-len(PROPERTY_ESTIMATION_METHOD__USED_PROPERTIES_SELECT_SUFFIX)]
            estimation_methods_name_list = EstimationMethodValue.get_expected_estimation_methods_name_list(property_name)
            select_used_property = Select(select_used_property)
            self.assertEqual(set(estimation_methods_name_list), {option.text for option in select_used_property.options})
            
            if property_name in used_properties_estimation_method:
                selected_estimation_method = select_used_property.first_selected_option.text
                (expected_selected_estimation_method, up_to_date) = used_properties_estimation_method[property_name]
                del used_properties_estimation_method[property_name]
                self.assertEqual(selected_estimation_method, expected_selected_estimation_method)
                self.assertEqual(up_to_date, PROPERTY_ESTIMATION_METHOD__USED_PROPERTY_OUT_OF_DATE_MESSAGE not in list_element.text)
            
            value_element = list_element.find_element_by_name(property_name + PROPERTY_ESTIMATION_METHOD__USED_PROPERTIES_VALUE_SUFFIX)
            if value_element.get_attribute("value") == PROPERTY_ESTIMATION_METHOD__NOT_COMPUTED_VALUE:
                is_compute_button_enable = False
                
        self.assertEqual(is_compute_button_enable, self._find_submit_component(PROPERTY_ESTIMATION_METHOD__COMPUTE_BUTTON_VALUE).is_enabled())
        self.assertEqual(len(used_properties_estimation_method), 0)
        
    def _assert_parameters(self, parameters_value_dict):
        try:
            parameters_ul_element = self.driver.find_element_by_id(PROPERTY_ESTIMATION_METHOD__PARAMETERS_LIST_ID)
            parameters_input_element_list = parameters_ul_element.find_elements_by_tag_name("input")
            parameters_select_element_list = parameters_ul_element.find_elements_by_tag_name("select")
        except NoSuchElementException:
            parameters_input_element_list = []
            parameters_select_element_list = []
        
        # Check all parameters of type text, float, integer
        for parameter_element in parameters_input_element_list:
            parameter_name = parameter_element.get_attribute("name")[:-len(PROPERTY_ESTIMATION_METHOD__PARAMETER_NAME_SUFFIX)]
            parameter_value = parameter_element.get_attribute("value")
            if parameter_name in parameters_value_dict:
                self.assertEqual(str(parameter_value), str(parameters_value_dict[parameter_name]))
                del parameters_value_dict[parameter_name]
            
        # Check all parameters of type select
        for parameter_element in parameters_select_element_list:
            parameter_name = parameter_element.get_attribute("name")[:-len(PROPERTY_ESTIMATION_METHOD__PARAMETER_NAME_SUFFIX)]
            parameter_value = Select(parameter_element).first_selected_option.text
            if parameter_name in parameters_value_dict:
                self.assertEqual(str(parameter_value), str(parameters_value_dict[parameter_name]))
                del parameters_value_dict[parameter_name]
                        
        self.assertEqual(len(parameters_value_dict), 0)
        
    def _assert_compute_value(self, value):
        if value == PROPERTY_ESTIMATION_METHOD__NOT_COMPUTED_VALUE:
            raise RuntimeError("Tests won't make difference between this value and no computed value when checking if the delete button " +
                               "is enable. Consequently, this value must not be used in test cases.")
        if value is None:
            self.assertIn(PROPERTY_ESTIMATION_METHOD__NO_COMPUTE_VALUE_MESSAGE, self.driver.page_source)
            self.assertFalse(self._find_submit_component(PROPERTY_ESTIMATION_METHOD__DELETE_BUTTON_VALUE).is_enabled())
        else:
            self.assertIn(PROPERTY_ESTIMATION_METHOD__COMPUTE_VALUE_MESSAGE + str(value), " ".join(self.driver.page_source.split()))
            self.assertTrue(self._find_submit_component(PROPERTY_ESTIMATION_METHOD__DELETE_BUTTON_VALUE).is_enabled())
            
    def _assert_general_context_page(self, expected_descriptions_list = ["", "", "", "", "", ""]):
        if len(expected_descriptions_list) != 6:
            raise RuntimeError("There must be exactly 6 elements in the description list, but {0} were found".format(len(expected_descriptions_list)))
        self._assert_page(GENERAL_CONTEXT__SUB_TITLE)
        
        actual_descriptions_list = [self.driver.find_element_by_name(GENERAL_CONTEXT__CONTEXT_GENERAL_ID).text,
                                    self.driver.find_element_by_name(GENERAL_CONTEXT__ORGANIZATION_GENERAL_ID).text,
                                    self.driver.find_element_by_name(GENERAL_CONTEXT__PRODUCT_GENERAL_ID).text,
                                    self.driver.find_element_by_name(GENERAL_CONTEXT__STAKEHOLDER_GENERAL_ID).text,
                                    self.driver.find_element_by_name(GENERAL_CONTEXT__METHOD_GENERAL_ID).text,
                                    self.driver.find_element_by_name(GENERAL_CONTEXT__BUSINESS_GENERAL_ID).text]
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
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestGlobal)
    unittest.TextTestRunner().run(suite)
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    

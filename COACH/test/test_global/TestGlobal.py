"""
Created on 20 juin 2017

@author: francois
"""

# Set python import path to include COACH top directory
import os
import sys
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

MAIN_MENU__GOAL_MENU = "Goal"

MAIN_MENU__CONTEXT_MENU = "Context"

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

#add_alternative_dialogue.html
ADD_ALTERNATIVE__SUB_TITLE = "Add new decision alternative"
ADD_ALTERNATIVE__TITLE_FIELD_NAME = "title"
ADD_ALTERNATIVE__DESCRIPTION_FIELD_NAME = "description"
ADD_ALTERNATIVE__CONFIRMATION_MESSAGE = "New alternative added!"

#properties_overview_dialogue.html
PROPERTY_OVERVIEW__SUB_TITLE = "Properties"

#properties_estimation_methods_dialogue.html
PROPERTY_ESTIMATION_METHOD__SUB_TITLE = "Estimation methods"
PROPERTY_ESTIMATION_METHOD__ALTERNATIVE_SELECT_NAME = "alternative_name"
PROPERTY_ESTIMATION_METHOD__PROPERTY_SELECT_NAME = "property_name"
PROPERTY_ESTIMATION_METHOD__ESTIMATION_METHOD_SELECT_NAME = "estimation_method_name"
PROPERTY_ESTIMATION_METHOD__NO_COMPUTE_VALUE_MESSAGE = "This estimation has not been computed yet"
PROPERTY_ESTIMATION_METHOD__COMPUTE_VALUE_MESSAGE = "Current value is "


# TODO: to suppress
from datetime import datetime
import inspect

def log(*args):
    message = datetime.now().strftime("%H:%M:%S") + " : "
    message += str(inspect.stack()[1][1]) + "::" + str(inspect.stack()[1][3]) + " : " #FileName::CallerMethodName
    for arg in args:
        message += str(arg) + " "
    print(message)
    sys.stdout.flush()

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
        self.current_case = None
        self.alternatives_name_list = []
        self.estimation_value_list = []
        
    def test_property_estimation_method(self):
        #Set up
        self._login()
        self._go_to_link(MAIN_MENU__CASE_MENU, MAIN_MENU__NEW_CASE_LINK, CREATE_CASE__SUB_TITLE)
        self._create_case("case")
        self._go_to_link(MAIN_MENU__ALTERNATIVES_MENU, MAIN_MENU__ADD_ALTERNATIVE_LINK, ADD_ALTERNATIVE__SUB_TITLE)

        self._add_alternative("Alt 1")
        self._assert_alternative_added()
        self._go_to_link(MAIN_MENU__PROPERTIES_MENU, MAIN_MENU__PROPERTY_OVERVIEW_LINK, PROPERTY_OVERVIEW__SUB_TITLE, 300)
        self._assert_property_overview_page()
        self._click_on_property_overview_shortcut("Alt 1", "Cost", "Expert estimate float")
        self._assert_property_estimation_method_page("Alt 1", "Cost", "Expert estimate float")
        self._assert_compute_value(None)
        self._compute({"estimation": 5})
        self.estimation_value_list.append(("Alt 1", "Cost", "Expert estimate float", 5.0))
        self._assert_compute_value(5)
        self._go_to_link(MAIN_MENU__PROPERTIES_MENU, MAIN_MENU__PROPERTY_OVERVIEW_LINK, PROPERTY_OVERVIEW__SUB_TITLE, 30)
        self._assert_property_overview_page()
        
    
    def _login(self):
        login_field = self.driver.find_element_by_name(INITIAL__USER_FIELD_NAME)
        password_field = self.driver.find_element_by_name(INITIAL__PASSWORD_FIELD_NAME)
        login_field.clear()
        login_field.send_keys(INITIAL__USER_NAME)
        password_field.clear()
        password_field.send_keys(INITIAL__PASSWORD)
        password_field.submit()
        WebDriverWait(self.driver, 5).until(EC.title_is(MAIN_MENU__PAGE_TITLE))
        
    
    def _go_to_link(self, menu_name, link_name, destination_sub_title_name, timeout = 5):
        menu = self.driver.find_element_by_link_text(menu_name)
        hover = ActionChains(self.driver).move_to_element(menu)
        hover.move_by_offset(1, 1)
        hover.perform()
        
        WebDriverWait(self.driver, 1).until(EC.visibility_of_element_located((By.LINK_TEXT, link_name)))
        link = self.driver.find_element_by_link_text(link_name)
        link.click()
        WebDriverWait(self.driver, timeout).until(EC.text_to_be_present_in_element((By.TAG_NAME, "h2"), destination_sub_title_name))
    
    def _open_case(self, case_name):
        self.current_case = case_name
        case_to_open_link = self.driver.find_element_by_link_text(case_name)
        case_to_open_link.click()
        WebDriverWait(self.driver, 5).until(EC.text_to_be_present_in_element((By.TAG_NAME, "h2"), CASE_STATUS__SUB_TITLE))
        
    def _create_case(self, case_name, case_description = "desc"):
        self.current_case = case_name
        title_field = self.driver.find_element_by_name(CREATE_CASE__TITLE_FIELD_NAME)
        description_field = self.driver.find_element_by_name(CREATE_CASE__DESCRIPTION_FIELD_NAME)
        title_field.clear()
        title_field.send_keys(case_name)
        description_field.clear()
        description_field.send_keys(case_description)
        description_field.submit()
        WebDriverWait(self.driver, 5).until(EC.text_to_be_present_in_element((By.TAG_NAME, "h2"), CASE_STATUS__SUB_TITLE))
        
    def _add_alternative(self, alternative_name, alternative_description = "desc"):
        self.alternatives_name_list.append(alternative_name)
        title_field = self.driver.find_element_by_name(ADD_ALTERNATIVE__TITLE_FIELD_NAME)
        description_field = self.driver.find_element_by_name(ADD_ALTERNATIVE__DESCRIPTION_FIELD_NAME)
        title_field.clear()
        title_field.send_keys(alternative_name)
        description_field.clear()
        description_field.send_keys(alternative_description)
        description_field.submit()
        WebDriverWait(self.driver, 5).until(EC.invisibility_of_element_located((By.TAG_NAME, "h2")))
        
    def _click_on_property_overview_shortcut(self, alternative_name, property_name, estimation_method_name):
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
                link.find_element_by_tag_name("div").click()
                WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "select")))
                return
        raise RuntimeError("The link (" + alternative_name + ", " + property_name + ", " + estimation_method_name + 
                           ") should have been clicked.")
        
    def _compute(self, parameters_dict = {}, used_properties_dict = {}):
        for parameter_name in parameters_dict:
            parameter_value = parameters_dict[parameter_name]
            try:
                parameter_element = Select(self.driver.find_element_by_name(parameter_name + "_parameter"))
                parameter_element.select_by_visible_text(parameter_value)
            except UnexpectedTagNameException:
                parameter_element = self.driver.find_element_by_name(parameter_name + "_parameter")
                parameter_element.clear()
                parameter_element.send_keys(str(parameter_value))
        
        for used_property_name in used_properties_dict:
            used_property_estimation_method = used_properties_dict[used_property_name]
            used_property_element = Select(self.driver.find_element_by_name(used_property_name + "_selected_estimation_method"))
            used_property_element.select_by_visible_text(used_property_estimation_method)
        
        submit_elements = self.driver.find_elements_by_name("submit_component")
        for submit_element in submit_elements:
            if submit_element.get_attribute("value") == "Compute":
                submit_element.click()
                WebDriverWait(self.driver, 60).until(EC.staleness_of(submit_element))
                return
            
    
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
    
    def _assert_alternative_added(self):
        self.assertIn(ADD_ALTERNATIVE__CONFIRMATION_MESSAGE, self.driver.page_source)
        
    def _assert_property_overview_page(self):
        self._assert_page(PROPERTY_OVERVIEW__SUB_TITLE)
        actual_estimation_method_value = EstimationMethodValue.build_from_web_page(self.driver)
        expected_estimation_method_value = EstimationMethodValue.build_expected_result(self.alternatives_name_list, self.estimation_value_list)
        log("actual :", actual_estimation_method_value)
        log("expected :", expected_estimation_method_value)
        self.assertEqual(actual_estimation_method_value, expected_estimation_method_value)
        
    def _assert_property_estimation_method_page(self, alternative_name = None, property_name = None, estimation_method_name = None):
        self._assert_page(PROPERTY_ESTIMATION_METHOD__SUB_TITLE)
        alternative_select = Select(self.driver.find_element_by_name(PROPERTY_ESTIMATION_METHOD__ALTERNATIVE_SELECT_NAME))
        property_select = Select(self.driver.find_element_by_name(PROPERTY_ESTIMATION_METHOD__PROPERTY_SELECT_NAME))
        estimation_method_select = Select(self.driver.find_element_by_name(PROPERTY_ESTIMATION_METHOD__ESTIMATION_METHOD_SELECT_NAME))
        
        if alternative_name is not None:
            self.assertEqual(alternative_name, alternative_select.first_selected_option.text)
        if property_name is not None:
            self.assertEqual(property_name, property_select.first_selected_option.text)
        if estimation_method_name is not None:
            self.assertEqual(estimation_method_name, estimation_method_select.first_selected_option.text)
        
        self.assertEqual(self.alternatives_name_list, [option.text for option in alternative_select.options])
        
        properties_name_list = EstimationMethodValue.get_default_properties_name_list()
        self.assertEqual(properties_name_list, [option.text for option in property_select.options])
        
        estimation_methods_name_list = EstimationMethodValue.get_default_estimation_methods_name_list(property_select.first_selected_option.text)
        self.assertEqual(estimation_methods_name_list, [option.text for option in estimation_method_select.options])
        
    def _assert_compute_value(self, value):
        if value is None:
            self.assertIn(PROPERTY_ESTIMATION_METHOD__NO_COMPUTE_VALUE_MESSAGE, self.driver.page_source)
        else:
            self.assertIn(PROPERTY_ESTIMATION_METHOD__COMPUTE_VALUE_MESSAGE + str(value), self.driver.page_source)
    
if __name__ == "__main__":
    print("TestGlobal main")
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestGlobal)
    unittest.TextTestRunner().run(suite)

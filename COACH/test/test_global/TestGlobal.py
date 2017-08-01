"""
Created on 20 juin 2017

@author: francois
"""
import sys
import os

sys.path.append(os.path.join(os.curdir, os.pardir, os.pardir, os.pardir))

import collections

import unittest

from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.select import Select
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import UnexpectedTagNameException

from contextlib import contextmanager

class TestGlobal (unittest.TestCase):
    #The name of each constant is <page name>__<constant name>

    #Addresses
    MAIN_PAGE_ADDRESS = "http://127.0.0.1:5000"
    
    #initial_dialogue.html
    INITIAL__PAGE_TITLE = "COACH"
    INITIAL__USER_FIELD_NAME = "user_id"
    INITIAL__PASSWORD_FIELD_NAME = "password"
    INITIAL__USER_NAME_1 = "user1"
    INITIAL__PASSWORD_1 = "password"
    INITIAL__USER_NAME_2 = "user2"
    INITIAL__USER_NAME_3 = "user3"
    INITIAL__PASSWORD_3 = "password"
    
    #main_menu.html
    MAIN_MENU__PAGE_TITLE = "COACH decision support system"
    
    MAIN_MENU__CASE_MENU = "Case"
    MAIN_MENU__OPEN_CASE_LINK = "Open case"
    MAIN_MENU__NEW_CASE_LINK = "New case"
    MAIN_MENU__CASE_STATUS_LINK = "Case status"
    MAIN_MENU__CASE_DESCRIPTION_LINK = "Case description"
    MAIN_MENU__EXPORT_CASE_LINK = "Export case to knowledge repository"
    MAIN_MENU__CLOSE_CASE = "Close case"
    MAIN_MENU__COMPUTE_SIMILARITY = "Compute similarity"
    
    MAIN_MENU__GOAL_MENU = "Goal"
    MAIN_MENU__GOAL_CUSTOMER_VALUE = "Customer value"
    MAIN_MENU__GOAL_FINANCIAL_VALUE = "Financial value"
    MAIN_MENU__GOAL_INTERNAL_BUSINESS_VALUE = "Internal business value"
    MAIN_MENU__GOAL_INNOVATION_AND_LEARNING_VALUE = "Innovation and learning value"
    MAIN_MENU__GOAL_MARKET_VALUE = "Market value"
    
    MAIN_MENU__CONTEXT_MENU = "Context"
    MAIN_MENU__CONTEXT_GENERAL = "General"
    MAIN_MENU__CONTEXT_ORGANIZATION = "Organization"
    MAIN_MENU__CONTEXT_PRODUCT = "Product"
    MAIN_MENU__CONTEXT_STAKEHOLDER = "Stakeholder"
    MAIN_MENU__CONTEXT_METHOD = "Development methods and technology"
    MAIN_MENU__CONTEXT_BUSINESS = "Market and business"
    
    MAIN_MENU__STAKEHOLDERS_MENU = "Stakeholders"
    MAIN_MENU__STAKEHOLDERS_EDIT = "Edit"
    
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
    
    #goal_dialogue.html
    GOAL_CATEGORY_CUSTOMER__PREFIX_ID = "SGR"
    GOAL_CATEGORY_FINANCIAL__PREFIX_ID = "SGR"
    GOAL_CATEGORY_INTERNAL_BUSINESS__PREFIX_ID = "SGR"
    GOAL_CATEGORY_INNOVATION_AND_LEARNING__PREFIX_ID = "SGR"
    GOAL_CATEGORY_MARKET__PREFIX_ID = "ESGR"

    #context_category_dialogue.html
    CONTEXT_CATEGORY__DEFAULT_COMBO_BOX_OPTION = "Unknown"
    CONTEXT_CATEGORY__TEXT_ENTRY_SUFFIX = "_text"
    CONTEXT_CATEGORY__SINGLE_SELECT_ENTRY_SUFFIX = "_single_select"
    CONTEXT_CATEGORY__MULTI_SELECT_ENTRY_SUFFIX = "_multi_select"
    CONTEXT_CATEGORY__INTEGER_ENTRY_SUFFIX = "_integer"
    CONTEXT_CATEGORY__FLOAT_ENTRY_SUFFIX = "_float"
    
    CONTEXT_CATEGORY_ORGANIZATION__SUB_TITLE = "Context details - Organization"
    CONTEXT_CATEGORY_ORGANIZATION__CONFIRMATION_MESSAGE = "Context information (organization) saved."
    
    #add_stakeholder.html
    STAKEHOLDER__ROLE_TITLE = "role_title"
    STAKEHOLDER__ROLE_LEVEL = "role_level"
    STAKEHOLDER__ROLE_FUNCTION = "role_function"
    STAKEHOLDER__ROLE_TYPE = "role_type"
    
    
    
    @classmethod
    def setUpClass(cls):
        super(TestGlobal, cls).setUpClass()
        cls.driver = webdriver.Firefox()
        
    @classmethod
    def tearDownClass(cls):
        super(TestGlobal, cls).tearDownClass()
        cls.driver.close()
        
    def setUp(self):
        self.driver.get(self.MAIN_PAGE_ADDRESS)
        self._assert_initial_page()
        self._login()
        self._assert_unactive_case()
        self._go_to_link(self.MAIN_MENU__CASE_MENU, self.MAIN_MENU__NEW_CASE_LINK)
        self._assert_page(self.CREATE_CASE__SUB_TITLE, False)
        self._create_case("case")
        self._assert_page(self.CASE_STATUS__SUB_TITLE)
        
        self.alternatives_name_list = []
        self.estimation_value_list = []
        
    def tearDown(self):
        self._go_to_link(self.MAIN_MENU__CASE_MENU, self.MAIN_MENU__CLOSE_CASE)
        self._check_check_box(self.CLOSE_CASE__EXPORT_TO_KR_CHECKBOX_NAME, False)
        self._select_combo_box(self.CLOSE_CASE__SELECTED_ALTERNATIVE_NAME, self.CLOSE_CASE__NONE_ALTERNATIVE)
          
        with self.wait_for_page_load():
            self.driver.find_element_by_tag_name("form").submit()
        self.assertIn(self.CLOSE_CASE__CONFIRMATION_MESSAGE, self.driver.page_source)
        
        
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
        
        
    def _select_combo_box(self, combo_box_identifier, option_name=None, page_load=False, timeout=5, option_name_list=None, by=By.NAME):
        """
        DESCRIPTION:
            Find the select element defined by combo_box_identifier and by, and select the provided option(s). If page_load is True, wait
            during timeout seconds until a new page is loaded before returning. In case of a multiple selection, clear the previous 
            selection before doing any new selection.
            If the combo box is a single combo box, and option name is already selected, it will return immediately, even if page_load
            is set to True. The same happens if the combo box is a multiple combo box, and option_name_list matches exactly the current
            selected options.
        INPUT:
            combo_box_identifier: The identifier used to find the combo box. This parameter and the "by" parameter are used together
                to create a locator.
            option_name: The name of a single option to select. Exactly one among option_name and option_name_list must be provided.
                If option_name is provided and the combo box is a multiple combo box, it is strictly identical as if
                option_name_list was provided as an iterable of 1 element. The selection is done according to the displayed text of the
                option, and not according to its value. The default value is None.
            page_load: If it is True, the function will wait for a new page being loaded before returning. If the combo box is a
                multiple combo box, and option_name_list contains more than 1 element, it will wait between each selection. The default
                value is False.
            timeout: The number of seconds to wait before raising a TimeoutException if a new page does not load.
            option_name_list: An iterator containing the name of options to select. Exactly one among option_name and option_name_list
                must be provided. If option_name_list is provided, but the combo box is a single combo box, a RuntimeError is raised,
                even if option_name_list contains only 1 element. The selection is done according to the displayed text of the option,
                and not according to its value. The default value is None.
            by: Defined how the combo box will be looked for. It forms a locator with combo_box_identifier. The default value is
                By.Name.
        OUTPUT:
            Return True if at least one selection has been performed, otherwise False. In other words, return False if the selected 
            option matches with the provided option_name for a single combo box, or if the selected options match with the provided
            option_name_list for a multiple combo box.
        ERROR:
            Raise a RuntimeError if neither or both of option_name and option_name_list are not None.
            Raise a RuntimeError if option_name_list is provided, but the combo box is a single combo box.
            Raise a TimeoutException if page_load is True but the page did not refresh in timeout seconds.
            Raise a StaleElementReferenceException if the combo box is a multiple combo box, more than one selection need to be done
                and page_load is False whereas the page is refreshed between each selection.
            Raise a UnexpectedTagNameException when the locator (combo_box_identifier, by) locates an element, but this element is
                not a combo box.
            Raise a NoSuchElementException when no element can be referred by the locator (combo_box_idenfifier, by).
        """
        if (option_name is None and option_name_list is None) or (option_name is not None and option_name_list is not None):
            raise RuntimeError("Exactly 1 among option_name and option_name_list must be None")
        
        select_element = self.driver.find_element(by, combo_box_identifier)
        is_multiple = select_element.get_attribute("multiple")
        select_element = Select(select_element)
        if option_name_list is not None and not is_multiple:
            raise RuntimeError("Can't select multiple value in a single select")
        
        if option_name is not None:
            # If the value is already selected, there is nothing to be done
            if select_element.first_selected_option.text == option_name:
                return False
            option_name_list = [option_name]
        
        if is_multiple:
            if set([option.text for option in select_element.all_selected_options]) == set(option_name_list):
                return False
                
            if page_load:
                # We have to deselect element one by one, as the select element will stale with deselect_all 
                while len(select_element.all_selected_options) != 0:
                    option = select_element.first_selected_option
                    with self.wait_for_page_load(timeout):
                        select_element.deselect_by_visible_text(option.text)
                    # As the page is reloaded, we have to look again for the element
                    select_element = Select(self.driver.find_element(by, combo_box_identifier))
            else:
                select_element.deselect_all()
                    
            
        for option_name in option_name_list:
            if page_load:
                with self.wait_for_page_load(timeout):
                    select_element.select_by_visible_text(option_name)
                    # As the page is reloaded, we have to look again for the element in case of multiple selection
                    select_element = Select(self.driver.find_element(by, combo_box_identifier))
            else:
                select_element.select_by_visible_text(option_name)
        return True

    def _send_key_in_field(self, field_identifier, message, clear=True, by=By.NAME):
        if not clear and message == "":
            return False
        
        text_field_element = self.driver.find_element(by, field_identifier)
        if clear:
            if text_field_element.get_attribute("value") == str(message):
                return False
            else:
                text_field_element.clear()
            
        text_field_element.send_keys(str(message))
        return True
        
    def _check_check_box(self, check_box_identifier, selected, by=By.NAME, page_load=False, timeout=5):
        check_box_element = self.driver.find_element(by, check_box_identifier)
        if check_box_element.is_selected() != selected:
            if page_load:
                with self.wait_for_page_load(timeout):
                    check_box_element.click()
            else:
                check_box_element.click()
    
    def _login(self, user_name=None, password=None):
        if user_name is None:
            user_name = self.INITIAL__USER_NAME_1
        if password is None:
            password = self.INITIAL__PASSWORD_1
            
        self._send_key_in_field(self.INITIAL__USER_FIELD_NAME, user_name)
        self._send_key_in_field(self.INITIAL__PASSWORD_FIELD_NAME, password)
        with self.wait_for_page_load():
            self.driver.find_element_by_tag_name("form").submit()
    
    def _logout(self):
        self.driver.get(self.MAIN_PAGE_ADDRESS)
        
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
    
    def _open_case(self, case_name, timeout=5):
        case_to_open_link = self.driver.find_element_by_link_text(case_name)
        with self.wait_for_page_load(timeout):
            case_to_open_link.click()
        
    def _create_case(self, case_name, case_description = "desc"):
        self._send_key_in_field(self.CREATE_CASE__TITLE_FIELD_NAME, case_name)
        self._send_key_in_field(self.CREATE_CASE__DESCRIPTION_FIELD_NAME, case_description)
        with self.wait_for_page_load():
            self.driver.find_element_by_tag_name("form").submit()
            
    def _open_or_create_case(self, case_name, case_description = "desc", timeout=20):
        self._go_to_link(self.MAIN_MENU__CASE_MENU, self.MAIN_MENU__OPEN_CASE_LINK)
        try:
            self._open_case(case_name, timeout)
        except NoSuchElementException:
            self._go_to_link(self.MAIN_MENU__CASE_MENU, self.MAIN_MENU__NEW_CASE_LINK)
            self._create_case(case_name, case_description)
            
    def _save_category_context(self, entries_value_dict):
        modification_has_been_done = False
        for entry_name in entries_value_dict:
            entry_value = entries_value_dict[entry_name]
            try:
                if (isinstance(entry_value, collections.Iterable) and not isinstance(entry_value, str)):
                    modification_has_been_done |= self._select_combo_box(entry_name, option_name_list=entry_value)
                else:
                    modification_has_been_done |= self._select_combo_box(entry_name, entry_value)
            except UnexpectedTagNameException: #Throw when trying to create a Select without a select element
                modification_has_been_done |= self._send_key_in_field(entry_name, entry_value)
                
        if modification_has_been_done:
            with self.wait_for_page_load(30):
                self.driver.find_element_by_tag_name("form").submit()
            
    def _save_goal_category(self, goal_boolean_dict):
        for goal_id in goal_boolean_dict:
            self._check_check_box(goal_id, goal_boolean_dict[goal_id], By.ID)
            
    def _save_stakeholders(self, stakeholder_dict):
       
        # The first line of the table is the headers, and we will not interact with them, the last line is the select to add
        # a new stakeholder
        tr_elements = self.driver.find_elements_by_tag_name("tr")[1:-1]
        stakeholders_in_case = {tr.find_elements_by_tag_name("td")[0].text for tr in tr_elements}
        
        # Add missing stakeholder to the case
        for stakeholder in stakeholder_dict:
            if stakeholder not in stakeholders_in_case:
                self._select_combo_box("select_new_stakeholder", stakeholder, True, by=By.ID)
                self._save_stakeholders(stakeholder_dict)
                return # The previous call to _save_stakeholder has done all the work, there is nothing left to be done.
        
        # Deselect all properties for unspecified stakeholders
        for stakeholder in stakeholders_in_case:
            if stakeholder not in stakeholder_dict:
                for category in [self.STAKEHOLDER__ROLE_FUNCTION, self.STAKEHOLDER__ROLE_LEVEL, self.STAKEHOLDER__ROLE_TITLE, 
                                 self.STAKEHOLDER__ROLE_TYPE]:
                    self._select_combo_box("select_" + category + "_" + stakeholder, page_load=True, option_name_list=[], by=By.ID)
        
        # Select specified values for stakeholders in stakeholder_dict
        for stakeholder in stakeholder_dict:
            for category in [self.STAKEHOLDER__ROLE_FUNCTION, self.STAKEHOLDER__ROLE_LEVEL, self.STAKEHOLDER__ROLE_TITLE, 
                                 self.STAKEHOLDER__ROLE_TYPE]:
                select_id = "select_" + category + "_" + stakeholder
                values_to_be_selected = stakeholder_dict[stakeholder][category]
                self._select_combo_box(select_id, page_load=True, option_name_list=values_to_be_selected, by=By.ID)
    
        
    def _assert_initial_page(self):
        self.assertIn(self.INITIAL__PAGE_TITLE, self.driver.title)
        
    def _assert_unactive_case(self):
        try:
            self.driver.find_element_by_link_text(self.MAIN_MENU__CASE_MENU) 
            self.driver.find_element_by_link_text(self.MAIN_MENU__OPEN_CASE_LINK)
            self.driver.find_element_by_link_text(self.MAIN_MENU__NEW_CASE_LINK)
            self.assertRaises(NoSuchElementException, self.driver.find_element_by_link_text, self.MAIN_MENU__CASE_STATUS_LINK)
            self.assertRaises(NoSuchElementException, self.driver.find_element_by_link_text, self.MAIN_MENU__CASE_DESCRIPTION_LINK)
            self.assertRaises(NoSuchElementException, self.driver.find_element_by_link_text, self.MAIN_MENU__EXPORT_CASE_LINK)
            self.assertRaises(NoSuchElementException, self.driver.find_element_by_link_text, self.MAIN_MENU__GOAL_MENU)
            self.assertRaises(NoSuchElementException, self.driver.find_element_by_link_text, self.MAIN_MENU__STAKEHOLDERS_MENU)
            self.assertRaises(NoSuchElementException, self.driver.find_element_by_link_text, self.MAIN_MENU__ALTERNATIVES_MENU)
            self.assertRaises(NoSuchElementException, self.driver.find_element_by_link_text, self.MAIN_MENU__PROPERTIES_MENU)
            self.assertRaises(NoSuchElementException, self.driver.find_element_by_link_text, self.MAIN_MENU__TRADE_OFF_MENU)
        except NoSuchElementException as e:
            self.fail(str(e))
    
    def _assert_active_case(self):
        try:
            self.driver.find_element_by_link_text(self.MAIN_MENU__CASE_MENU)
            self.driver.find_element_by_link_text(self.MAIN_MENU__OPEN_CASE_LINK)
            self.driver.find_element_by_link_text(self.MAIN_MENU__NEW_CASE_LINK)
            self.driver.find_element_by_link_text(self.MAIN_MENU__CASE_STATUS_LINK)
            self.driver.find_element_by_link_text(self.MAIN_MENU__CASE_DESCRIPTION_LINK)
            self.driver.find_element_by_link_text(self.MAIN_MENU__EXPORT_CASE_LINK)
            self.driver.find_element_by_link_text(self.MAIN_MENU__GOAL_MENU)
            self.driver.find_element_by_link_text(self.MAIN_MENU__STAKEHOLDERS_MENU)
            self.driver.find_element_by_link_text(self.MAIN_MENU__ALTERNATIVES_MENU)
            self.driver.find_element_by_link_text(self.MAIN_MENU__PROPERTIES_MENU)
            self.driver.find_element_by_link_text(self.MAIN_MENU__TRADE_OFF_MENU)
        except NoSuchElementException as e:
            self.fail(str(e))


    def _assert_page(self, page_sub_title, is_case_active = True):
        subTitle = self.driver.find_element_by_tag_name("h2")
        self.assertEqual(subTitle.text, page_sub_title)
        if is_case_active:
            self._assert_active_case()
        else:
            self._assert_unactive_case()
            
if __name__ == "__main__":
    suite = unittest.defaultTestLoader.discover(".", "Test*")
    unittest.TextTestRunner(verbosity=3).run(suite)
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    

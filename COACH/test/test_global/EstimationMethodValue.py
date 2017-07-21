"""
Created on 20 juin 2017

@author: francois
"""

class EstimationMethodValue():
    PROPERTY_ESTIMATION_METHOD = [
        {
            "property_name": "Cost",
            "estimation_methods": ["Cost estimation", "Expert estimate float"]
        },
        {
            "property_name": "Development effort",
            "estimation_methods": ["Intermediate COCOMO", "Basic COCOMO", "Expert estimate float"]
        },
        {
            "property_name": "KLOC",
            "estimation_methods": ["Expert estimate float"]
        },                          
        {
            "property_name": "Worst case execution time",
            "estimation_methods": ["Expert estimate integer"]
        }
    ]
    
    def __init__(self, properties_estimation):
        self.properties_estimation = properties_estimation
    
    @classmethod
    def build_from_web_page(cls, driver):
        table_element = driver.find_element_by_class_name("properties_estimation_table")       

        tr_elements = table_element.find_elements_by_tag_name("tr")
        th_alternatives = tr_elements[0].find_elements_by_tag_name("th")
        alternatives_name_list = [cell.text for cell in th_alternatives[2:]]
        
        properties_estimation = []
        i = 1
        while i < len(tr_elements):
            (th_property, th_estimation_method) = tr_elements[i].find_elements_by_tag_name("th")
            property_name = th_property.text
            properties_estimation.append({"property_name": property_name, "estimation_methods": []})
            
            estimation_method_name = th_estimation_method.text
            properties_estimation[-1]["estimation_methods"].append({"estimation_method_name": estimation_method_name,
                                                                    "estimation_method_values": []})
            cls._add_value_from_web_page(cls, tr_elements[i], alternatives_name_list, properties_estimation)
            estimation_methods_number = int(th_property.get_attribute("rowspan"))
            j = i + 1
            while j < i + estimation_methods_number:
                estimation_method_name = tr_elements[j].find_element_by_tag_name("th").text
                properties_estimation[-1]["estimation_methods"].append({"estimation_method_name": estimation_method_name,
                                                                        "estimation_method_values": []})
                cls._add_value_from_web_page(cls, tr_elements[j], alternatives_name_list, properties_estimation)
                j += 1
                
            i += estimation_methods_number
        
        return cls(properties_estimation)
        
    def _add_value_from_web_page(self, current_tr_element, alternatives_name_list, properties_estimation):
        estimation_method_values = properties_estimation[-1]["estimation_methods"][-1]["estimation_method_values"]
        td_estimations = current_tr_element.find_elements_by_tag_name("td")
        for i, estimation_cell in enumerate(td_estimations):
            try:
                estimation_value = float(estimation_cell.text.strip())
            except ValueError:
                estimation_value = estimation_cell.text.strip()
            up_to_date = not ("out_of_date" in estimation_cell.get_attribute("class"))
            
            estimation_method_values.append({"alternative_name": alternatives_name_list[i],
                                             "up_to_date": up_to_date,
                                             "value": estimation_value})
    
    @classmethod
    def build_expected_result(cls, alternatives_name_list, values = []):
        properties_estimation = []
        for property_ in cls.PROPERTY_ESTIMATION_METHOD:
            estimation_methods = []
            for estimation_method_name in property_["estimation_methods"]:
                estimation_method_values = []
                for alternative_name in alternatives_name_list:
                    estimation_method_values.append({"alternative_name": alternative_name, "value": "", "up_to_date": True})
                estimation_methods.append({"estimation_method_name": estimation_method_name, 
                                           "estimation_method_values": estimation_method_values})
            properties_estimation.append({"property_name": property_["property_name"],
                                         "estimation_methods": estimation_methods})
        
        instance = cls(properties_estimation)
        instance.add_values(values)
        return instance
        
    def add_value(self, alternative_name, property_name, estimation_method_name, value, up_to_date = True):
        property_ = self._find_dictionary_in_list(self.properties_estimation, "property_name", property_name)
        for estimation_method in property_["estimation_methods"]:
            if estimation_method["estimation_method_name"] == estimation_method_name:
                estimation = self._find_dictionary_in_list(estimation_method["estimation_method_values"], "alternative_name", alternative_name)
                estimation["value"] = value
                estimation["up_to_date"] = up_to_date
            else:
                estimation = self._find_dictionary_in_list(estimation_method["estimation_method_values"], "alternative_name", alternative_name)
                if estimation["value"] == "":
                    estimation["value"] = "---"
                
    def add_values(self, values):
        for value in values:
            try:
                (alternative_name, property_name, estimation_method_name, value) = value
                up_to_date = True
            except ValueError:
                (alternative_name, property_name, estimation_method_name, value, up_to_date) = value
            
            if value == "":
                raise RuntimeError("The test can fail if an estimation is an empty string, whereas the application is ok:\n" +
                                   "If another estimation with the same alternative and property but different estimation method " +
                                   "has been computed after, this value will wrongly be replaced by '---' in the expected result.")
            self.add_value(alternative_name, property_name, estimation_method_name, value, up_to_date)
        
        
    def __eq__(self, other, self_name="self", other_name="other", verbose=True):
        if not isinstance(other, EstimationMethodValue):
            if verbose:
                print("{0} is not an EstimationMethodValue.".format(other_name))
            return False
        
        for i, self_property in enumerate(self.properties_estimation):
            other_property = other.properties_estimation[i]
            if len(self_property) != 2 or len(other_property) != 2:
                raise RuntimeError("Malformed object EstimationMethod : a property must have exactly 2 keys")
            if self_property["property_name"] != other_property["property_name"]:
                if verbose:
                    print("Properties differ between {0} and {1}. First different property: {2} in {0}, {3} in {1}."
                          .format(self_name, other_name, self_property["property_name"], other_property["property_name"]) )
                return False
            
            self_estimation_methods_list = self_property["estimation_methods"]
            other_estimation_methods_list = other_property["estimation_methods"]
            if len(self_estimation_methods_list) != len(other_estimation_methods_list):
                if verbose:
                    print(("There is not the same number of estimation method for the property {0} in {1} and {2}. In {1}: {3}, " +
                          "in {2}: {4}.").format(self_property["property_name"], self_name, other_name, len(self_estimation_methods_list), 
                                                  len(other_estimation_methods_list)))
                return False
            
            for self_estimation_method in self_estimation_methods_list:
                try:
                    other_estimation_method = self._find_dictionary_in_list(other_estimation_methods_list, "estimation_method_name", 
                                                                            self_estimation_method["estimation_method_name"])
                except RuntimeError:
                    if verbose:
                        print("The estimation method {0} is not in {1}'s property {2}".format(self_estimation_method["estimation_method_name"],
                                                                                                other_name, other_property["property_name"]))
                    return False
                if len(self_estimation_method) != 2 or len(other_estimation_method) != 2:
                    raise RuntimeError("Malformed object EstimationMethod : an estimation method must have exactly 2 keys")
                
                self_estimation_method_values_list = self_estimation_method["estimation_method_values"]
                other_estimation_method_values_list = other_estimation_method["estimation_method_values"]
                if len(self_estimation_method_values_list) != len(other_estimation_method_values_list):
                    if verbose:
                        print(("There is not the same number of values for the property {0} and the estimation method {1} in {2} and {3}. " +
                              "In {2}: {4}, in {3}: {5}").format(self_property["property_name"], 
                                                                 self_estimation_method["estimation_method_name"], self_name, other_name,
                                                                 len(self_estimation_method_values_list), 
                                                                 len(other_estimation_method_values_list)))
                    return False
                
                for self_estimation_method_value in self_estimation_method_values_list:
                    try:
                        other_estimation_method_value = self._find_dictionary_in_list(other_estimation_method_values_list, 
                                                                                      "alternative_name", 
                                                                                      self_estimation_method_value["alternative_name"])
                    except RuntimeError:
                        if verbose:
                            print("There is no estimation for ({0}, {1}, {2}) in {3}"
                                  .format(self_estimation_method_value["alternative_name"], self_property["property_name"],
                                          self_estimation_method["estimation_method_name"], other_name))
                        return False
                    if len(self_estimation_method_value) != 3 or len(other_estimation_method_value) != 3:
                        raise RuntimeError("Malformed object EstimationMethod : an estimation method value must have exactly 3 keys")
                    
                    if self_estimation_method_value["value"] != other_estimation_method_value["value"]:
                        if verbose:
                            print("The value of the estimation ({0}, {1}, {2}) is {3} in {4} and {5} in {6}"
                                  .format(self_estimation_method_value["alternative_name"], self_property["property_name"],
                                          self_estimation_method["estimation_method_name"], self_estimation_method_value["value"],
                                          self_name, other_estimation_method_value["value"], other_name))
                        return False
                    if self_estimation_method_value["up_to_date"] != other_estimation_method_value["up_to_date"]:
                        if verbose:
                            print("The estimation ({0}, {1}, {2}) has a up-to-date property {3} in {4} and {5} in {6}"
                                  .format(self_estimation_method_value["alternative_name"], self_property["property_name"],
                                          self_estimation_method["estimation_method_name"], self_estimation_method_value["up_to_date"],
                                          self_name, other_estimation_method_value["up_to_date"], other_name))
                        return False
                        
        return True
    
    def __str__(self):
        return str(self.properties_estimation)
        
    @classmethod
    def _find_dictionary_in_list(cls, dictionary_list, key_name, value):
        for dictionary in dictionary_list:
            if dictionary[key_name] == value:
                return dictionary
        raise RuntimeError("Dictionary with the property " + key_name + " equals to " + value + " not found.")
    
    @classmethod
    def get_expected_properties_name_list(cls):
        return [p["property_name"] for p in cls.PROPERTY_ESTIMATION_METHOD]
    
    @classmethod
    def get_expected_estimation_methods_name_list(cls, property_name):
        property_dictionary = cls._find_dictionary_in_list(cls.PROPERTY_ESTIMATION_METHOD, "property_name", property_name)
        return property_dictionary["estimation_methods"]
        
        
        
        
        
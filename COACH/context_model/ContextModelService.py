"""
Created on June 22, 2016

@author: Jan Carlson

The context model service
"""

"""
TODO:

- Only the first of multiple selection alternatives are sent when the button is pressed.
Sending it using method="get" includes all selected alternatives. Question is when duplicates of the same parameter are discarded


- Button size (MAC bug):
Possible workaround, but not so nice:
input[type=submit] {
  font-weight: bold;
  font-size: 150%;
}

- Some selections should also have a text field (treat as a separate type "multiother")?

- Protection against "no value" also for radio buttons, similar to selections (if there is no value, the parameter will not be included in the request at all, so the lookup will fail  

- Should be possible to have a "no answer" value also in the radio buttons.

- Now each contaxt entry is saved as a separate case fact. Is it better to save the whole context as a single fact?

- Now all values are represented as strings when stored in the case fact (e.g., "Low" or "Aerospace/Aviation"). Is this ok?

"""

# Set python import path to include COACH top directory
import os
import sys
sys.path.append(os.path.join(os.curdir, os.pardir, os.pardir, os.pardir))


# Coach framework
from COACH.framework import coach
from COACH.framework.coach import endpoint

# Web server framework
from flask.templating import render_template
from flask import request


class ContextModelService(coach.Microservice):

    organization = [{},{},{},{},{},{},{},{},{},{},{},{}]

    organization[0]["id"] = "O1"
    organization[0]["description"] = "Application domain of the organization(s) (e.g. working with automotive, avionics, telecommunication, etc.)."
    organization[0]["type"] = "multi"
    organization[0]["alternatives"] = [
    "Accounting", 
    "Aerospace/Aviation",
    "Advertising",
    "Agriculture/Forestry/Fishing",
    "Automotive",
    "Biotechnology",
    "Business/Professional Services",
    "Computer (Software)",
    "Computer (Hardware)",
    "Construction/Home Improvement",
    "Consulting",
    "Corporate Communication",
    "Education",
    "Engineering/Architecture",
    "Entertainment/Recreation",
    "Finance/Banking/Insurance",
    "Food Service",
    "Government/Military",
    "Healthcare/Medical",
    "Internet/eCommerce",
    "Logistics/Shipping",
    "Manufacturing",
    "Mobile Applications",
    "Services (Hotels, Lodging Places)",
    "Telecommunication"
    ]
    organization[0]["guideline"] = "Select your primary application domain(s)."


    organization[1]["id"] = "O2"
    organization[1]["description"] = "Degree of distribution of the development site (consider factors such as local or global/distributed development with multiple development sites, multiple geographical locations, national or international)."
    organization[1]["type"] = "radio"
    organization[1]["alternatives"] = ["Low", "Medium", "High"]
    organization[1]["guideline"] = "Low distribution = same room or building\nMedium distribution = same area or within driving/commuting distance, locally distributed\nMedium to High distribution = large driving/commuting distance but within same time zone, locally distributed, on-shore\nHigh distribution = Within a 3-hour time zone difference, off-shore\nVery High distribution = Some are in areas with greater than 3 hours time zone difference, long off-shore"

    organization[2]["id"] = "O3"
    organization[2]["description"] = "Stability of the organization - frequency of changes in the organizational environment (structural, managerial, operational, strategic, etc.)."
    organization[2]["type"] = "radio"
    organization[2]["alternatives"] = ["Low", "Medium", "Medium to high", "High", "Very high"]
    organization[2]["guideline"] = "Very Low stability = frequent changes on strategic level\nLow stability = frequent changes on operational/managerial level\nMedium stability = changes occur every 1-3 years\nHigh stability = changes occur every 3-5 years\nVery High stability = changes are very rare"

    organization[3]["id"] = "O4"
    organization[3]["guideline"] = ""
    organization[3]["description"] = "The current business strategy or goal of the organization - referring to what the organization wants to achieve in the near future."
    organization[3]["type"] = "text"
    
    organization[4]["id"] = "O51"
    organization[4]["guideline"] = ""
    organization[4]["description"] = "The size of the organization (development site) in terms of the number of people."
    organization[4]["type"] = "integer"

    organization[5]["id"] = "O52"
    organization[5]["guideline"] = ""
    organization[5]["description"] = "The size of your team in terms of the number of people."
    organization[5]["type"] = "integer"

    organization[6]["id"] = "O6"
    organization[6]["description"] = "Maturity and process certification (maturity of the organization with respect to process capabilities, e.g. initial, repeatable, defined, managed and optimized processes, certified through e.g. ISO and CMMI)."
    organization[6]["type"] = "multi"
    organization[6]["alternatives"] = [
    "CMM",
    "CMMI",
    "SW-CMM",
    "P-CMM",
    "91",
    "ISO 9001:2000",
    "ISO 9000 series",
    "TickIT",
    "Bootstrap",
    "ISO/IEC 12207",
    "ISO/IEC 15504",
    "SPICE",
    "SPIRE",
    "PMBOK",
    "SWEBOK",
    "MOF",
    "Six Sigma",
    "IDEAL",
    "QIP",
    "PDCA(PDSA)",
    "Trillium",
    "TQM",
    "COBIT",
    "SEI TSP",
    "SEI PSP",
    "Accounting"
    ]
    organization[6]["guideline"] = ""

    organization[7]["id"] = "O7"
    organization[7]["description"] = "Capacity and team resources (availability of critical resources for projects, such as availability of physical working environments, housing facilities, skilled team, experts, senior managements' commitment)."
    organization[7]["type"] = "radio"
    organization[7]["alternatives"] = ["Underload", "Good capacity utilization", "High capacity utilization", "High overload,", "Critical overload"]
    organization[7]["guideline"] = "Underload utilization = An underload utilization is when resources are used or loaded incompletely.\nGood capacity utilization = A good capacity utilization is when resources are used just right.\nHigh capacity utilization = A high capacity utilization is when the maximum amount of utilization has been reached.\nHigh overload = A high overload situtation means that there is a higher load than the capacity, and this makes the process flow almost jammed (analogous to road highways jams). If the capacity is almost completely utilized (the highway is quite full) then the flow moves slower, but still has a steady flow.\nCritical overload = A critical overload situation means that there is a substantial higher load than the capacity, and this is causing the flow to be almost standstill."        

    organization[8]["id"] = "O8"
    organization[8]["description"] = "Average throughput and velocity of the organization (considering factors such as number of projects/year, average meantime between project deliveries, flexibility of the organization in terms of ability to change without negative impact)."
    organization[8]["type"] = "radio"
    organization[8]["alternatives"] = ["Low", "Medium", "High"]
    organization[8]["guideline"] = ""

    organization[9]["id"] = "O10"
    organization[9]["description"] = "Organizational model - Characteristics that apply to the organization."
    organization[9]["type"] = "multi"
    organization[9]["alternatives"] = [
    "Bureaucratic",
    "Project team structure",
    "Matrix structure",
    "Virtual",
    "Other"
    ]
    organization[9]["guideline"] = "Bureaucratic - Tall organisation with hierarchical structures and centralised power\nProject team structure - Team-based organization\nMatrix structure: Combination of bureaucratic and project team structure\nVirtual: Teams collaborate virtually and collaborate in a distributed environment"

    organization[10]["id"] = "O11"
    organization[10]["description"] = "Degree by which the organization is affected by external/outside relations, such as relations maintained with customers, partners, suppliers and competitors."
    organization[10]["type"] = "radio"
    organization[10]["alternatives"] = ["Low", "Medium", "High"]
    organization[10]["guideline"] = ""


    organization[11]["id"] = "O12"
    organization[11]["guideline"] = ""
    organization[11]["description"] = "Other... (please describe the missing aspect(s))"
    organization[11]["type"] = "text"
    



    product = []

    product.append({
      'id' : 'P1',
      'description' : 'Maturity of the product (related to how long it has been on the market, how many releases were there, certifications obtained, etc.).',
      'type' : 'radio',
      'alternatives' : ['Low', 'Medium', 'High'],
      'guideline' : 'Low maturity: The software has been recently released and not widely or commonly known nor used.\nMedium maturity: The software has been on the market or in use for a long time, but known defects have not been removed nor has the functionality of the software been evolved to better fit the needs of the market.\nHigh maturity: The software has been on the market or in use for a long time and has established itself as a widely used software product. The software has matured in terms of its quality (e.g. defects in the code)',
      })
  
    product.append({
      'id' : 'P2',
      'description' : 'The degree of technical debt of the product.',
      'type' : 'radio',
      'alternatives' : ['Low', 'Medium', 'High'],
      'guideline' : 'Low = None of the debts (code, design and architecture, or test) is significant for the product\nMedium = Only one type of debt (either code, design and architecture, or test) is significant for the product\nHigh = high degree of technical debt in the code (poorly written), the design and architecture (poor upfront design with under-focus on qualitties such as maintainability and adaptability) and test debt (lack of test scripts and insufficient test coverage)',
      })
  
    product.append({
      'id' : 'P3',
      'description' : 'System type (e.g. embedded, real-time, information system).',
      'type' : 'multi',
      'alternatives' : [
        'Consumer-oriented software',
        'Business-oriented software',
        'Design and engineering software',
        'Information display and transaction entry',
        'Operating systems',
        'Networking / Communications',
        'Device / Peripheral drivers',
        'Support utilities',
        'Middleware and system components',
        'Software Backplanes (e.g. Eclipse)',
        'Servers',
        'Malware',
        'Hardware control',
        'Embedded software',
        'Real time control software',
        'Process control software (i.e. air traffic control, industrial process, nuclear plants)',
        'Operations research',
        'Information management and manipulation',
        'Artistic creativity',
        'Scientific software',
        'Artificial intelligence'
      ],
      'guideline' : '',
      })
  
    product.append({
      'id' : 'P4',
      'description' : 'Complexity of the system (considering factors such as size in term of lines of code, number of sub-systems, structural complexity of the control flow, complexity of data structures).',
      'type' : 'radio',
      'alternatives' : ['Low', 'Medium', 'High'],
      'guideline' : 'Low complexity: Small scale applications and systems, usually few sub-systems or individual systems\nMedium complexity: Systems of either large scale in terms of size or consisting of multiple systems (system of systems)\nHigh complexity: Systems of large scale in terms of size and consisting of multiple systems (system of systems) with complex interactions and dependencies',
      })
  
    product.append({
      'id' : 'P5',
      'description' : 'Degree to which the system or parts of the system (building blocks such as components) can be reused.',
      'type' : 'radio',
      'alternatives' : ['Low', 'Medium', 'High'],
      'guideline' : 'Based on three factors: a) The systems interfaces are documented clearly to facilitate reuse; b) The user interfaces to the system are stable; and c) The system can be configured to facilitate reuse in different contexts.\nLow reuse: None or max one of a), b), and c) are fulfilled.Medium reuse: Two out of three a), b) and c) are fulfilled.\nHigh reuse: All three of a), b), and c) are fulfilled.',
      })
  
    product.append({
      'id' : 'P6',
      'description' : 'Main functional purpose of the product',
      'type' : 'text',
      'guideline' : '',
      })

    product.append({
      'id' : 'P7',
      'description' : 'Quality attributes that are prioritized as most important for the product.',
      'type' : 'multi',
      'alternatives' : [
        'Functional suitability',
        'Performance efficiency',
        'Compatibility',
        'Usability',
        'Reliability',
        'Security',
        'Maintainability',
        'Portability'
      ],
      'guideline' : '',
      })

    product.append({
      'id' : 'P8',
      'description' : 'Certification and rules/regulations/standards (e.g. mandatory compliances to for example safety, security).',
      'type' : 'multi',
      'alternatives' : [
        'ISO26262',
        'ISO13849',
        'ISO15998',
        'ISO/IEC27001',
        'IEC62443',
        'IEC61508',
        'IEC61131-6',
        'EN50126',
        'EN50128',
        'EN50129'
      ],
      'guideline' : '',
      })


    product.append({
      'id' : 'P9',
      'description' : 'How much of the product is available for modification by the developers?',
      'type' : 'radio',
      'alternatives' : ['Low', 'Medium', 'High'],
      'guideline' : '',
      })

    product.append({
      'id' : 'P10',
      'description' : 'Main programming languages used in the development of the product.',
      'type' : 'multi',
      'alternatives' : [
        'Access',
        'Ada',
        'ASP',
        'Assembly',
        'Basic',
        'C',
        'C#',
        'C++',
        'CLIPPER',
        'COBOL',
        'CUDA',
        'EJB',
        'Erlang',
        'Haskell',
        'IIS',
        'J2EE Servlet/JSP',
        'Java',
        'Javascript',
        'Lua',
        'NATURAL',
        'NOTES',
        'Objective-C',
        'OpenCL',
        'ORACLE',
        'Pascal',
        'Perl',
        'PHP',
        'PL/I',
        'PLEX',
        'Prolog',
        'Python',
        'Ruby',
        'Simulink',
        'TELON',
        'Visual Basic'
      ],
      'guideline' : '',
      })


    product.append({
      'id' : 'P11',
      'description' : 'Intellectual property rights (e.g., patents, copyrights and trademarks).',
      'type' : 'radio',
      'alternatives' : ['Low', 'Medium', 'High'],
      'guideline' : 'Control and rights over IR (Intellectual Propery) is understood as the combination of internal or external (3rd party, community) level of control and ownership of trademarks, copyright, patents, industrial design rights, and in some jurisdictions trade secrets.\nLow: A company does not have ownership, it is owned and controlled by others.\nMedium: A company shares the right to use, adapt and distribute but the ownership is still placed fully or partly (shared) within the company. The company defines certain conditions and rules of licencing.\nHigh: A company has full ownership and has the right to use, adapt, copy and distribute the product',
      })

    product.append({
      'id' : 'P12',
      'description' : 'Other... (please describe the missing aspect(s))',
      'type' : 'text',
      'guideline' : '',
      })


    stakeholders = []

    stakeholders.append({
      'id' : 'S1',
      'description' : 'Stakeholder roles.',
      'type' : 'multi',
      'alternatives' : [
        'Business (internal)',
        'Sales and marketing (internal)',
        'Asset supplier (internal)',
        'Consulting and services (internal)',
        'Financial control (internal)',
        'Asset user (internal)',
        'Researcher (internal)',
        'Operational control (internal)',
        'Quality assurance (internal)',
        'Production (internal)',
        'Product management (internal)',
        'Legal (internal)',
        'Governmental (internal)',
        'Association regulator (internal)',
        'Assessor (internal)',
        'Keystone (internal)',
        'Manufacturer (internal)',
        'Content provider (internal)',
        'Service provider (internal)',
        'Service operator (internal)',
        'Integrator (internal)',
        'Product owner (internal)',
        'Regulatory agency (internal)',
        'End user (internal)',
        'Business (external)',
        'Sales and marketing (external)',
        'Asset supplier (external)',
        'Consulting and services (external)',
        'Financial control (external)',
        'Asset user (external)',
        'Researcher (external)',
        'Operational control (external)',
        'Quality assurance (external)',
        'Production (external)',
        'Product management (external)',
        'Legal (external)',
        'Governmental (external)',
        'Association regulator (external)',
        'Assessor (external)',
        'Keystone (external)',
        'Manufacturer (external)',
        'Content provider (external)',
        'Service provider (external)',
        'Service operator (external)',
        'Integrator (external)',
        'Product owner (external)',
        'Regulatory agency (external)',
        'End user (external)'
        ],
      'guideline' : 'Internal = role is within the organization\nExternal = role is outside the organization'
      })
  
    stakeholders.append({
      'id' : 'S2',
      'description' : 'Stakeholder experience with respect to the product.',
      'type' : 'radio',
      'alternatives' : ['Low', 'Medium', 'High'],
      'guideline' : 'Low: worked with the product for less than a year OR only works with the product sporadically (i.e. the work related to the product is not the main focus)\nMedium: worked with the product for more than a year and less than two years AND the work with the product was the main focus of the work\nHigh: worked with the product for more than two years AND the work with the product was the main focus of the work'
      })

    stakeholders.append({
      'id' : 'S3',
      'description' : 'Other... (please describe the missing aspect(s))',
      'type' : 'text',
      'guideline' : ''
      })

  
  
    methods = []

    methods.append({
      'id' : 'M1',
      'description' : 'Development methods.',
      'type' : 'multi',
      'alternatives' : [
        'Agile Software Development (ASD)',
        'Crystal Methods',
        'Dynamic Systems Development Model (DSDM)',
        'Extreme Programming (XP)', 
        'Feature Driven Development (FDD)',
        'Joint Application Development (JAD)',
        'Lean Development (LD)',
        'Rapid Application Development (RAD)',
        'Rational Unified Process (RUP)',
        'Scrum',
        'Spiral',
        'Systems Development Life Cycle (SDLC)',
        'Waterfall (a.k.a. Traditional/Plan-driven)'
        ],
      'guideline' : ''
      })
  
    methods.append({
      'id' : 'M2',
      'description' : 'Development practices.',
      'type' : 'multi',
      'alternatives' : [
        'Up-front documentation of requirements',
        'Detailed up-front architecture design',
        'Big bang integration and infrequent releases',
        'Extensive time planning',
        'Sequential flow of project phases',
        'Repeatable development process',
        'Technical excellence',
        'Small self-organizing cross-functional teams',
        'On-site customer',
        'Frequent planning/reporting',
        'Pair-programming',
        'Continuous integration with testing',
        'Iteration reviews, retrospectives',
        'Test-driven development',
        'Collective code ownership',
        'Continuous deployment',
        'Component based development', 
        'Model-driven development'
        ],
      'guideline' : 'Up-front documentation of requirements: Requirements are fully documented and as complete as possible\nDetailed up-front architecture design: Detailed and extensive design of entire software architecture, documentation-heavy\nBig bang integration and infrequent releases: Most of the implementation artifacts, such as code and modules, are integrated at once before milestones; releases are done at least once per 4 months or more\nExtensive time planning: Fully specified Gantt charts with fixed milestones for the entire project, complete work breakdown structure decomposition,\nSequential flow of project phases: When one phase is finished, it is closed, e.g., requirements, design, construction, testing, delivery.\nDetailed management plans and process documentation: Formal and plan-based quality, risk, resource, change, and configuration management\nRepeatable development process: The process is formally defined and followed, it is repeatable, its flexibility and abilities to adapt to projects are limited\nFace-to-face communication: Team sits together, open space office facilitating interaction, video conferences if the team is distributed\nTechnical excellence: Ongoing refactoring of the code, simplest solution design, following coding standards\nSmall self-organizing cross-functional teams\nOn-site customer: Continuous user involvement in the development process, customer can be consulted anytime if it is needed\nFrequent planning/reporting: Everyday meetings to discuss what was and what is going to be done, reporting the progress on a burn-down chart, burn-up chart, informative workshops\nPrioritized list of requirements: Tasks in a backlog as features/user stories—short statements of the functionality, system metaphors—stories about how the system works\nPair-programming: Two developers work together at one workstation, they switch roles\nTime-boxing: Fixed time of iterations, meetings, working hours limited to 40 h weekly—employees hardly ever work overtime, no ‘‘death march’’ projects, team members avoid burnout, etc.\nContinuous integration with testing: Software is built frequently, even few times a day, accompanied with testing (e.g., ten-minute builds, automated unit, regression, etc.)\nShort iterations and releases: Frequent releases of the software, at most 3–4 months, early and continuous delivery of partial but fully functional software\nIteration reviews, retrospectives: The entire team participates in selecting features to be implemented in the following iteration, estimating resources required to implement them, consensus based, e.g., planning game, the Wideband Delphi Estimation, planning poker, etc.\nIteration reviews, retrospectives: Meetings after each iteration to review the project, discuss threats to process efficiency, modify, and improve, build up the software development process\nTest-driven development: Writing automated test cases for functionalities and then implementing the tested functionalities until the tests are passed successfully\nCollective code ownership: Everybody in the team can change the code of other developers in case of maintenance, bug fixing or other development activities teams: The team is independent, takes full responsibility; small with no more than 10 members\nContinuous deployment: Changes to the system are continuously deployed in the target environment of the user\nComponent based development: Software built from independent software components with explicit dependencies\nModel-driven development: Models are the main development artifact, from which code is generated'
      })

    methods.append({
      'id' : 'M3',
      'description' : 'Development environments and CASE tools used in the development of the product.',
      'type' : 'multi',
      'alternatives' : [
        'Android Studio', 
        'Codenvy', 
        'Delphi', 
        'Eclipse', 
        'Enterprise Architect', 
        'GCC', 
        'Git', 
        'IntelliJ', 
        'Komodo', 
        'MATLAB', 
        'MATLAB/Simulink', 
        'Microsoft Visual Studio', 
        'NetBeans', 
        'Oracle JDeveloper', 
        'Papyrus', 
        'Rational ClearCase', 
        'Rational DOORS', 
        'Rational Rhapsody', 
        'Rubus ICE', 
        'Sublime Text', 
        'Subversion', 
        'SystemWeaver', 
        'Vim', 
        'Volcano Vehicle System Architect', 
        'Xamarin', 
        'Xcode', 
        'Xojo'
        ],
      'guideline' : ''
      })
 
    methods.append({
      'id' : 'M4',
      'description' : 'Level of maturity of technologies, development methods and CASE tools used in the development of the product',
      'type' : 'radio',
      'alternatives' : ['TRL 1', 'TRL 2', 'TRL 3', 'TRL 4', 'TRL 5', 'TRL 6', 'TRL 7', 'TRL 8', 'TRL 9'],
      'guideline' : 'TRL 1: Basic principles observed\nTRL 2: Technology concept formulated\nTRL 3: Experimental proof of concept\nTRL 4: Technology validated in lab\nTRL 5: Technology validated in relevant environment (industrially relevant environment in the case of key enabling technologies)\nTRL 6: Technology demonstrated in relevant environment (industrially relevant environment in the case of key enabling technologies)\nTRL 7: System prototype demonstration in operational environment\nTRL 8: System complete and qualified\nTRL 9: Actual system proven in operational environment (competitive manufacturing in the case of key enabling technologies; or in space)'
      })

    methods.append({
      'id' : 'M5',
      'description' : 'Ratio of proprietory and open technologies and CASE tools used in the development of the product.',
      'type' : 'integer',
      'guideline' : '0%: No proprietary tools and technologies, only open.\n100% Only proprietary tools and technologies, no open.'
      })

    methods.append({
      'id' : 'M6',
      'description' : 'Other... (please describe the missing aspect(s))',
      'type' : 'text',
      'guideline' : ''
      })




    business = []  
  
    business.append({
      'id' : 'B1',
      'description' : 'Type of market and market structure (e.g. monopolistic competition, oligopoly, oligopsony)',
      'type' : 'multi',
      'alternatives' : ['Monopolistic competition', 'Oligopoly', 'Monopsony', 'Oligopsony', 'Monopoly', 'Perfect competition'],
      'guideline' : '"Monopolistic competition = a type of imperfect competition such that many producers sell products or services that are differentiated from one another (e.g. by branding or quality) and hence are not perfect substitutes.\nOligopoly = a market is run by a small number of firms that together control the majority of the market share.\nMonopsony = when there is only a single buyer in a market.\nOligopsony = a market where many sellers can be present but meet only a few buyers.\nMonopoly = there is only one provider of a product or service.\nPerfect competition = a market with low barriers to entry, identical products with no differentiation, an unlimited number of producers and consumers, and a perfectly elastic demand curves.'
      })
 
    business.append({
      'id' : 'B2',
      'description' : 'The level at which the market is affected by rules, regulations, and standards (e.g. certification, government imposed requirements)',
      'type' : 'radio',
      'alternatives' : ['Not at all', 'Slightly', 'Moderately', 'Very', 'Extremely'],
      'guideline' : ''
      }) 

    business.append({
      'id' : 'B3',
      'description' : 'Description of the market landscape (e.g. competitors, suppliers, partners, customers).',
      'type' : 'text',
      'guideline' : ''
      })

    business.append({
      'id' : 'B4',
      'description' : 'The degree of time pressure to release on the market indicating the speed of evolution in market trends.',
      'type' : 'radio',
      'alternatives' : ['Not at all', 'Very little', 'Somewhat', 'To a great extent'],
      'guideline' : ''
      }) 

    business.append({
      'id' : 'B5',
      'description' : 'Significant factors affecting the status of the market (e.g. external pressures, political factors).',
      'type' : 'text',
      'guideline' : ''
      })

    business.append({
      'id' : 'B6',
      'description' : 'Quality of the external relations of the organization with other stakeholders and ecosystems (includes level of trust, support, commitment among the parties).',
      'type' : 'radio',
      'alternatives' : ['Very poor', 'Poor', ' Acceptable', 'Good', 'Very good'],
      'guideline' : ''
      }) 

    business.append({
      'id' : 'B7',
      'description' : 'Type of contracts or agreements related to the requirements, payments, etc.,  (whether these are signed from the start and are stable/fixed, or created and discussed during the project, more flexible/adaptable).',
      'type' : 'radio',
      'alternatives' : ['Stable contracts and agreements', 'Flexible and adaptable contracts and agreements'],
      'guideline' : 'Stable = signed at the start of the project and remain fixed over a period of time, \nFlexible and adaptable = contracts/agreements change during the project'
      }) 

    business.append({
      'id' : 'B8',
      'description' : 'Other... (please describe the missing aspect(s))',
      'type' : 'text',
      'guideline' : ''
      })
      
      



    @endpoint("/edit_context_dialogue", ["GET"], "text/html")
    def edit_context_dialogue_transition(self, user_id, delegate_token, case_db, case_id):
        """
        Endpoint which lets the user edit context information.
        """
        
        case_db_proxy = self.create_proxy(case_db)
       
        values = {}
        
        values['C'] = case_db_proxy.get_case_property(user_id = user_id, token = delegate_token, case_id = case_id, name = "context_C")
        values['O'] = case_db_proxy.get_case_property(user_id = user_id, token = delegate_token, case_id = case_id, name = "context_O")
        values['P'] = case_db_proxy.get_case_property(user_id = user_id, token = delegate_token, case_id = case_id, name = "context_P")
        values['S'] = case_db_proxy.get_case_property(user_id = user_id, token = delegate_token, case_id = case_id, name = "context_S")
        values['M'] = case_db_proxy.get_case_property(user_id = user_id, token = delegate_token, case_id = case_id, name = "context_M")
        values['B'] = case_db_proxy.get_case_property(user_id = user_id, token = delegate_token, case_id = case_id, name = "context_B")
        
        for e in self.product :
            values[e['id']] = case_db_proxy.get_case_property(user_id = user_id, token = delegate_token, case_id = case_id, name = "context_"+e['id'])
        for e in self.organization :
            values[e['id']] = case_db_proxy.get_case_property(user_id = user_id, token = delegate_token, case_id = case_id, name = "context_"+e['id'])
        for e in self.stakeholders :
            values[e['id']] = case_db_proxy.get_case_property(user_id = user_id, token = delegate_token, case_id = case_id, name = "context_"+e['id'])
        for e in self.methods :
            values[e['id']] = case_db_proxy.get_case_property(user_id = user_id, token = delegate_token, case_id = case_id, name = "context_"+e['id'])
        for e in self.business :
            values[e['id']] = case_db_proxy.get_case_property(user_id = user_id, token = delegate_token, case_id = case_id, name = "context_"+e['id'])

        #print("XXXX values XXX")
        #print(values)
        #print("XXXXXXXXXXXXXXX")
        
        return render_template(
          "edit_context_dialogue.html",
          organization = self.organization,
          product = self.product,
          stakeholders = self.stakeholders,
          methods = self.methods,
          business = self.business,
          values = values)     



    @endpoint("/edit_context", ["POST"], "text/html")
    def edit_context(self, user_id, delegate_token, case_db, case_id):
        """
        This method is called using POST when the user presses the save button in the edit_context_dialogue_transition.
        It gets several form parameters: 
        case_id : The ID of the current case
        context_text : The text entered in the main context text area
        It writes the new context information to the database, and then returns a status message to be shown in the main dialogue window.
        """
        # DEBUGGING
        print("XXXX str(request.values)) XXX")
        print(str(request.values))
        print("XXXXXXXXXXXXXXXXXXXXXXXXXXXXX")
        
        
        # Write the new context information to the database.
        case_db_proxy = self.create_proxy(case_db)
        
        case_db_proxy.change_case_property(user_id = user_id, token = delegate_token, case_id = case_id, name = "context_C", value = request.values["C-text"] if "C-text" in request.values else "")
        
        case_db_proxy.change_case_property(user_id = user_id, token = delegate_token, case_id = case_id, name = "context_O", value = request.values["O-text"] if "O-text" in request.values else "")
        case_db_proxy.change_case_property(user_id = user_id, token = delegate_token, case_id = case_id, name = "context_P", value = request.values["P-text"] if "P-text" in request.values else "")
        case_db_proxy.change_case_property(user_id = user_id, token = delegate_token, case_id = case_id, name = "context_S", value = request.values["S-text"] if "S-text" in request.values else "")
        case_db_proxy.change_case_property(user_id = user_id, token = delegate_token, case_id = case_id, name = "context_M", value = request.values["M-text"] if "M-text" in request.values else "")
        case_db_proxy.change_case_property(user_id = user_id, token = delegate_token, case_id = case_id, name = "context_B", value = request.values["B-text"] if "B-text" in request.values else "")

        for e in self.organization :
            case_db_proxy.change_case_property(user_id = user_id, token = delegate_token, case_id = case_id, name = "context_"+e['id'], value = request.values[e['id']+'-'+e['type']] if e['id']+'-'+e['type'] in request.values else "")         
        for e in self.product :
            case_db_proxy.change_case_property(user_id = user_id, token = delegate_token, case_id = case_id, name = "context_"+e['id'], value = request.values[e['id']+'-'+e['type']] if e['id']+'-'+e['type'] in request.values else "")         
        for e in self.stakeholders :
            case_db_proxy.change_case_property(user_id = user_id, token = delegate_token, case_id = case_id, name = "context_"+e['id'], value = request.values[e['id']+'-'+e['type']] if e['id']+'-'+e['type'] in request.values else "")         
        for e in self.methods :
            case_db_proxy.change_case_property(user_id = user_id, token = delegate_token, case_id = case_id, name = "context_"+e['id'], value = request.values[e['id']+'-'+e['type']] if e['id']+'-'+e['type'] in request.values else "")         
        for e in self.business :
            case_db_proxy.change_case_property(user_id = user_id, token = delegate_token, case_id = case_id, name = "context_"+e['id'], value = request.values[e['id']+'-'+e['type']] if e['id']+'-'+e['type'] in request.values else "")         
    
        return "Context information saved."
    
    
if __name__ == '__main__':
    ContextModelService(sys.argv[1]).run()

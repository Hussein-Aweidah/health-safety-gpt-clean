import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import streamlit as st

class ComplianceChecker:
    """Compliance gap checking system for NZ health and safety standards."""
    
    def __init__(self):
        self.compliance_data_file = "user_data/compliance_assessments.json"
        self.ensure_data_directory()
        
    def ensure_data_directory(self):
        """Ensure the user_data directory exists."""
        os.makedirs("user_data", exist_ok=True)
        if not os.path.exists(self.compliance_data_file):
            self.initialize_compliance_data()
    
    def initialize_compliance_data(self):
        """Initialize the compliance data structure."""
        initial_data = {
            "assessments": [],
            "templates": self.get_default_templates(),
            "last_updated": datetime.now().isoformat()
        }
        with open(self.compliance_data_file, 'w') as f:
            json.dump(initial_data, f, indent=2)
    
    def get_default_templates(self) -> Dict:
        """Get default compliance assessment templates for different industries."""
        return {
            "construction": {
                "name": "Construction Site Safety",
                "categories": [
                    {
                        "name": "Personal Protective Equipment (PPE)",
                        "requirements": [
                            "Hard hats available and worn",
                            "High-visibility clothing provided",
                            "Safety footwear required",
                            "Eye protection available",
                            "Hearing protection provided"
                        ]
                    },
                    {
                        "name": "Site Safety",
                        "requirements": [
                            "Site boundaries clearly marked",
                            "Safety signage visible",
                            "Emergency procedures documented",
                            "First aid kits accessible",
                            "Fire extinguishers available"
                        ]
                    },
                    {
                        "name": "Equipment Safety",
                        "requirements": [
                            "Equipment inspections documented",
                            "Operator training verified",
                            "Maintenance schedules current",
                            "Safety guards in place",
                            "Warning systems functional"
                        ]
                    }
                ]
            },
            "healthcare": {
                "name": "Healthcare Facility Safety",
                "categories": [
                    {
                        "name": "Infection Control",
                        "requirements": [
                            "Hand hygiene protocols",
                            "PPE availability",
                            "Waste disposal procedures",
                            "Cleaning schedules",
                            "Isolation protocols"
                        ]
                    },
                    {
                        "name": "Patient Safety",
                        "requirements": [
                            "Patient identification procedures",
                            "Medication safety protocols",
                            "Fall prevention measures",
                            "Emergency response plans",
                            "Incident reporting systems"
                        ]
                    }
                ]
            },
            "manufacturing": {
                "name": "Manufacturing Safety",
                "categories": [
                    {
                        "name": "Machine Safety",
                        "requirements": [
                            "Machine guards installed",
                            "Emergency stop buttons",
                            "Lockout/tagout procedures",
                            "Operator training completed",
                            "Maintenance records current"
                        ]
                    },
                    {
                        "name": "Chemical Safety",
                        "requirements": [
                            "SDS sheets available",
                            "Chemical storage proper",
                            "Spill response procedures",
                            "Ventilation systems working",
                            "PPE provided for chemicals"
                        ]
                    }
                ]
            },
            "general": {
                "name": "General Workplace Safety",
                "categories": [
                    {
                        "name": "Workplace Environment",
                        "requirements": [
                            "Adequate lighting",
                            "Proper ventilation",
                            "Temperature control",
                            "Clean and organized",
                            "Emergency exits clear"
                        ]
                    },
                    {
                        "name": "Employee Training",
                        "requirements": [
                            "Induction training completed",
                            "Role-specific training",
                            "Emergency procedures training",
                            "Regular refresher training",
                            "Training records maintained"
                        ]
                    }
                ]
            }
        }
    
    def create_assessment(self, business_name: str, industry: str, assessor: str) -> str:
        """Create a new compliance assessment."""
        assessment_id = f"assessment_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        template = self.get_default_templates().get(industry, self.get_default_templates()["general"])
        
        assessment = {
            "id": assessment_id,
            "business_name": business_name,
            "industry": industry,
            "assessor": assessor,
            "created_date": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "status": "in_progress",
            "categories": [],
            "overall_score": 0,
            "total_requirements": 0,
            "compliant_requirements": 0,
            "action_items": []
        }
        
        # Initialize categories from template
        for cat in template["categories"]:
            category = {
                "name": cat["name"],
                "requirements": [],
                "score": 0,
                "total_reqs": len(cat["requirements"]),
                "compliant_reqs": 0
            }
            
            for req in cat["requirements"]:
                requirement = {
                    "text": req,
                    "status": "not_assessed",
                    "compliance_level": "unknown",
                    "evidence": "",
                    "notes": "",
                    "priority": "medium",
                    "action_required": "",
                    "target_date": "",
                    "assigned_to": ""
                }
                category["requirements"].append(requirement)
            
            assessment["categories"].append(category)
            assessment["total_requirements"] += category["total_reqs"]
        
        # Save assessment
        self.save_assessment(assessment)
        return assessment_id
    
    def save_assessment(self, assessment: Dict):
        """Save an assessment to the data file."""
        data = self.load_compliance_data()
        
        # Update existing or add new
        existing_index = None
        for i, existing in enumerate(data["assessments"]):
            if existing["id"] == assessment["id"]:
                existing_index = i
                break
        
        if existing_index is not None:
            data["assessments"][existing_index] = assessment
        else:
            data["assessments"].append(assessment)
        
        data["last_updated"] = datetime.now().isoformat()
        
        with open(self.compliance_data_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_compliance_data(self) -> Dict:
        """Load compliance data from file."""
        try:
            with open(self.compliance_data_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            self.initialize_compliance_data()
            return self.load_compliance_data()
    
    def get_assessment(self, assessment_id: str) -> Optional[Dict]:
        """Get a specific assessment by ID."""
        data = self.load_compliance_data()
        for assessment in data["assessments"]:
            if assessment["id"] == assessment_id:
                return assessment
        return None
    
    def update_requirement_status(self, assessment_id: str, category_index: int, 
                                req_index: int, status: str, compliance_level: str, 
                                evidence: str = "", notes: str = "", priority: str = "medium",
                                action_required: str = "", target_date: str = "", 
                                assigned_to: str = "") -> bool:
        """Update the status of a specific requirement."""
        assessment = self.get_assessment(assessment_id)
        if not assessment:
            return False
        
        if (category_index < len(assessment["categories"]) and 
            req_index < len(assessment["categories"][category_index]["requirements"])):
            
            req = assessment["categories"][category_index]["requirements"][req_index]
            req["status"] = status
            req["compliance_level"] = compliance_level
            req["evidence"] = evidence
            req["notes"] = notes
            req["priority"] = priority
            req["action_required"] = action_required
            req["target_date"] = target_date
            req["assigned_to"] = assigned_to
            
            # Update category and overall scores
            self.calculate_scores(assessment)
            
            # Save updated assessment
            self.save_assessment(assessment)
            return True
        
        return False
    
    def calculate_scores(self, assessment: Dict):
        """Calculate compliance scores for categories and overall assessment."""
        total_compliant = 0
        
        for category in assessment["categories"]:
            category_compliant = 0
            for req in category["requirements"]:
                if req["status"] == "compliant":
                    category_compliant += 1
                    total_compliant += 1
            
            category["compliant_reqs"] = category_compliant
            if category["total_reqs"] > 0:
                category["score"] = (category_compliant / category["total_reqs"]) * 100
        
        assessment["compliant_requirements"] = total_compliant
        if assessment["total_requirements"] > 0:
            assessment["overall_score"] = (total_compliant / assessment["total_requirements"]) * 100
    
    def generate_gap_analysis(self, assessment_id: str) -> Dict:
        """Generate a comprehensive gap analysis report."""
        assessment = self.get_assessment(assessment_id)
        if not assessment:
            return {}
        
        gaps = {
            "assessment_id": assessment_id,
            "business_name": assessment["business_name"],
            "generated_date": datetime.now().isoformat(),
            "overall_compliance": assessment["overall_score"],
            "critical_gaps": [],
            "high_priority_gaps": [],
            "medium_priority_gaps": [],
            "low_priority_gaps": [],
            "action_plan": [],
            "timeline_recommendations": [],
            "resource_requirements": []
        }
        
        # Analyze gaps by priority
        for category in assessment["categories"]:
            for req in category["requirements"]:
                if req["status"] != "compliant":
                    gap_item = {
                        "category": category["name"],
                        "requirement": req["text"],
                        "current_status": req["status"],
                        "priority": req["priority"],
                        "action_required": req["action_required"],
                        "target_date": req["target_date"],
                        "assigned_to": req["assigned_to"]
                    }
                    
                    if req["priority"] == "critical":
                        gaps["critical_gaps"].append(gap_item)
                    elif req["priority"] == "high":
                        gaps["high_priority_gaps"].append(gap_item)
                    elif req["priority"] == "medium":
                        gaps["medium_priority_gaps"].append(gap_item)
                    else:
                        gaps["low_priority_gaps"].append(gap_item)
        
        # Generate action plan
        gaps["action_plan"] = self.generate_action_plan(gaps)
        
        return gaps
    
    def generate_action_plan(self, gaps: Dict) -> List[Dict]:
        """Generate a prioritized action plan based on gap analysis."""
        action_plan = []
        
        # Critical gaps - immediate action required
        for gap in gaps["critical_gaps"]:
            action_plan.append({
                "action": f"Address {gap['requirement']} in {gap['category']}",
                "priority": "Critical",
                "timeline": "Immediate (within 24 hours)",
                "resources_needed": "Management approval, immediate resources",
                "assigned_to": gap["assigned_to"] or "Management",
                "estimated_cost": "High - immediate allocation required"
            })
        
        # High priority gaps - within 1 week
        for gap in gaps["high_priority_gaps"]:
            action_plan.append({
                "action": f"Implement {gap['requirement']} in {gap['category']}",
                "priority": "High",
                "timeline": "Within 1 week",
                "resources_needed": "Department resources, training if needed",
                "assigned_to": gap["assigned_to"] or "Department Head",
                "estimated_cost": "Medium - planned allocation"
            })
        
        # Medium priority gaps - within 1 month
        for gap in gaps["medium_priority_gaps"]:
            action_plan.append({
                "action": f"Plan and implement {gap['requirement']} in {gap['category']}",
                "priority": "Medium",
                "timeline": "Within 1 month",
                "resources_needed": "Regular planning cycle",
                "assigned_to": gap["assigned_to"] or "Team Leader",
                "estimated_cost": "Low - regular budget"
            })
        
        return action_plan
    
    def get_assessment_summary(self, assessment_id: str) -> Dict:
        """Get a summary of assessment results."""
        assessment = self.get_assessment(assessment_id)
        if not assessment:
            return {}
        
        return {
            "id": assessment["id"],
            "business_name": assessment["business_name"],
            "industry": assessment["industry"],
            "created_date": assessment["created_date"],
            "overall_score": assessment["overall_score"],
            "total_requirements": assessment["total_requirements"],
            "compliant_requirements": assessment["compliant_requirements"],
            "status": assessment["status"],
            "categories_summary": [
                {
                    "name": cat["name"],
                    "score": cat["score"],
                    "total": cat["total_reqs"],
                    "compliant": cat["compliant_reqs"]
                }
                for cat in assessment["categories"]
            ]
        }
    
    def list_assessments(self) -> List[Dict]:
        """List all assessments with summary information."""
        data = self.load_compliance_data()
        return [self.get_assessment_summary(assessment["id"]) 
                for assessment in data["assessments"]]
    
    def export_assessment_report(self, assessment_id: str, format: str = "json") -> str:
        """Export assessment report in specified format."""
        assessment = self.get_assessment(assessment_id)
        gaps = self.generate_gap_analysis(assessment_id)
        
        if format == "json":
            report = {
                "assessment": assessment,
                "gap_analysis": gaps,
                "export_date": datetime.now().isoformat(),
                "export_format": "json"
            }
            return json.dumps(report, indent=2)
        
        # Add more export formats here as needed
        return "Export format not supported"

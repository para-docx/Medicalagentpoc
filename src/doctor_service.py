from datetime import datetime
import streamlit as st

class DoctorService:
    def __init__(self, doctors_collection, llm_service):
        self.doctors = doctors_collection
        self.llm_service = llm_service

    def find_specialization(self, symptoms):
        try:
            specializations = self.doctors.distinct("specialization") or ["General Practitioner"]
            
            prompt = f"""Analyze these symptoms: {', '.join(symptoms)}
            Recommend a specialization from this list: {', '.join(specializations)}
            Return only the specialization name from the list."""
            
            response = self.llm_service.get_response(prompt)
            
            if response:
                spec = response.strip()
                if spec in specializations:
                    return spec
                for s in specializations:
                    if spec.lower() in s.lower() or s.lower() in spec.lower():
                        return s
            return "General Practitioner"
        except Exception as e:
            st.error(f"Specialization error: {str(e)}")
            return "General Practitioner"

    def check_availability(self, specialization):
        current_day = datetime.now().strftime("%A")
        current_time_str = datetime.now().strftime("%H:%M")
        days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        today_idx = days_order.index(current_day)
        doctors_list = []

        try:
            for doc in self.doctors.find({"specialization": specialization}):
                doctor_info = self._get_doctor_info(doc, current_day, current_time_str, days_order, today_idx)
                doctors_list.append(doctor_info)
            return doctors_list
        except Exception as e:
            st.error(f"Database error: {str(e)}")
            return []

    def _get_doctor_info(self, doc, current_day, current_time_str, days_order, today_idx):
        doctor_info = {
            "name": doc.get("name", "Unknown Doctor"),
            "available_now": False,
            "current_slots": 0,
            "next_available": None
        }

        for slot in doc.get("availability", []):
            if self._is_currently_available(slot, current_day, current_time_str, doc):
                doctor_info["available_now"] = True
                doctor_info["current_slots"] = slot["max_patients"] - doc["current_appointments"]
                break

        if not doctor_info["available_now"]:
            doctor_info["next_available"] = self._get_next_slot(doc, days_order, today_idx, current_time_str)

        return doctor_info

    def _get_next_slot(self, doctor, days_order, today_idx, current_time_str):
        for offset in range(7):
            day_idx = (today_idx + offset) % 7
            day = days_order[day_idx]
            
            for slot in doctor.get("availability", []):
                slot_day = slot.get("day", "").strip().lower()
                if slot_day == day.lower():
                    if day.lower() == datetime.now().strftime("%A").lower():
                        if slot.get("start") > current_time_str:
                            return {
                                "day": "Today",
                                "time": f"{slot['start']}-{slot['end']}",
                                "slots": slot.get("max_patients", 0) - doctor.get("current_appointments", 0)
                            }
                    else:
                        return {
                            "day": day,
                            "time": f"{slot['start']}-{slot['end']}",
                            "slots": slot.get("max_patients", 0) - doctor.get("current_appointments", 0)
                        }
        return None

    def _is_currently_available(self, slot, current_day, current_time_str, doc):
        slot_day = slot.get("day", "").strip().lower()
        return (slot_day == current_day.lower() and
                slot.get("start") <= current_time_str <= slot.get("end") and
                doc.get("current_appointments", 0) < slot.get("max_patients", 0))


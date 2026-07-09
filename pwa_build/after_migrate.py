import os
import frappe
import json
from frappe.utils import update_progress_bar
from frappe.modules import import_file
from frappe.query_builder import DocType

class AfterMigrate:
	def __init__(self):
		self.sync_pwa_forms()
		apply_nav_order()

	def sync_pwa_forms(self):
		apps = frappe.get_installed_apps()
		for app_name in apps:
			folder_path = frappe.get_app_path(app_name, app_name,"pwa_form")
			if os.path.exists(folder_path):
				for i, fname in enumerate(os.listdir(folder_path)):
					update_progress_bar(f"Updating PWA Forms for {app_name}", i, len(os.listdir(folder_path)))
					frappe.local.flags.in_patch = True
					import_forms(os.path.join(folder_path, fname))
					frappe.local.flags.in_patch = False
					frappe.clear_cache()
				# print each progress bar on new line
				print()
							
def apply_nav_order():
	"""Stamp modified timestamps in reverse nav order so the bundled frontend's
	default `modified desc` listing renders screens in the designed flow order."""
	from frappe.utils import add_to_date, now_datetime

	rows = []
	for doctype in ("PWA Form", "PWA Dashboard"):
		rows += [(doctype, row.name, row.nav_order) for row in frappe.get_all(doctype, fields=["name", "nav_order"])]

	if not any(row[2] for row in rows):
		return

	rows.sort(key=lambda row: (row[2] is None, row[2] or 0))
	base = now_datetime()
	for position, (doctype, name, _nav_order) in enumerate(rows):
		frappe.db.set_value(
			doctype, name, "modified", add_to_date(base, seconds=-position), update_modified=False
		)


def import_forms(file_path):
	try:
		docs = import_file.read_doc_from_file(file_path)
	except IOError:
		print(file_path + " missing")
		return

	calculated_hash = import_file.calculate_hash(file_path)
	if docs:
		if not isinstance(docs, list):
			docs = [docs]
		for doc in docs:
			
			stored_hash = None
			if doc["form_name"] and doc["doctype_name"]:
				if doc["doctype_name"] == "Dashboard":
					stored_hash = get_stored_hash("PWA Dashboard", doc)
				else:
					stored_hash = get_stored_hash("PWA Form", doc)
	 
			if stored_hash and stored_hash == calculated_hash:
				continue

			#delete existing form if it exists
			check_doc_exists(
				"PWA Dashboard" if doc["doctype_name"] == "Dashboard" else "PWA Form",
				doc
			)
			#create new form
			create_form_records(doc)

			#update hash value
			doctype_table = DocType("PWA Form")
			frappe.qb.update(doctype_table).set(doctype_table.document_hash_value, calculated_hash).where(
				(doctype_table.form_name == doc["form_name"]) & (doctype_table.doctype_name == doc["doctype_name"])
			).run()
   
def get_stored_hash(doctype, doc):
	try:
		return frappe.db.get_value(doctype,{"form_name":doc["form_name"],"doctype_name":doc["doctype_name"]}, "document_hash_value")
	except Exception:
		return None

def check_doc_exists(doctype, doc):
	if doc := frappe.db.exists(doctype, {"form_name":doc["form_name"],"doctype_name":doc["doctype_name"]}):
		frappe.delete_doc(doctype, doc, force=1, for_reload=True)

def create_form_records(docdict):
	overall_json = dict(docdict)
 
	DocType = "PWA Dashboard" if docdict["doctype_name"] == "Dashboard" else "PWA Form"
 		
	docdict["__islocal"] = 1
	docdict["doctype"] = DocType
	docdict.pop("pwa_form_fields")

	doc = frappe.get_doc(docdict)
	if docdict["doctype_name"] == "Dashboard":
		doc.pwa_dashboard_fields=json.dumps(overall_json,indent=4)
	else:
		doc.pwa_form_fields=json.dumps(overall_json,indent=4)
	doc.flags.ignore_version = True
	doc.flags.ignore_links = True
	doc.flags.ignore_validate = True
	doc.flags.ignore_permissions = True
	doc.flags.ignore_mandatory = True
	doc.insert()

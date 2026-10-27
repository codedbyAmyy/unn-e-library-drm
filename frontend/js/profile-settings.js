import { apiRequest } from "./api.js";

const make = (tag, className = "", value = "") => {
  const element = document.createElement(tag);
  element.className = className;
  element.textContent = value;
  return element;
};
const statusText = (role) => role.charAt(0).toUpperCase() + role.slice(1);

export async function showProfileSettings({ content, user, onSaved }) {
  content.replaceChildren();
  const title = make("div", "pf-heading");
  title.append(make("div", "pf-eyebrow", "ACCOUNT PREFERENCES"), make("h1", "", "Profile & Account Settings"), make("p", "pf-sub", "Manage your personal information and academic affiliation."));
  content.append(title);

  let departments = [];
  try {
    departments = await apiRequest("/academic/departments");
    if (!Array.isArray(departments)) throw Error("Invalid department list response.");
  } catch (err) {
    const note = make("p", "pf-message pf-error", `Department names could not be loaded: ${err.message}. Please confirm the academic lookup endpoint is installed.`);
    content.append(note);
  }

  let profile = user;
  try { profile = await apiRequest("/auth/me"); } catch (err) {
    content.append(make("p", "pf-message pf-error", err.message));
  }
  const departmentName = () => departments.find(d => Number(d.id) === Number(profile.department_id))?.name || (profile.department_id ? "Department not found in catalog" : "Not selected");

  const hero = make("section", "pf-hero");
  const avatar = make("span", "pf-avatar", (profile.full_name || "U").slice(0, 2).toUpperCase());
  const person = make("div", "pf-person");
  person.append(make("strong", "", profile.full_name || "Member"), make("span", "", profile.email || ""), make("span", "pf-role", statusText(profile.role)));
  const edit = make("button", "pf-button pf-secondary", "Edit Profile"); edit.type = "button";
  hero.append(avatar, person, edit);content.append(hero);

  const grid = make("div", "pf-grid");content.append(grid);
  const personal = make("section", "pf-card");personal.append(make("h2", "", "Personal Information"),make("p", "pf-card-desc", "Account details linked to your university identity."));
  const form = make("form", "pf-form");
  const name = document.createElement("input");name.value = profile.full_name || ""; name.required=true;name.maxLength=100; name.disabled=true;
  const email = document.createElement("input"); email.value=profile.email||"";email.disabled=true;
  const role = document.createElement("input");role.value=statusText(profile.role);role.disabled=true;
  const institution = document.createElement("input");institution.value="University of Nigeria, Nsukka"; institution.disabled=true;
  const dept = document.createElement("select");dept.disabled=true;
  dept.append(new Option("No department selected", ""));
  for (const d of departments) dept.add(new Option(d.name + (d.code ? ` (${d.code})` : ""),String(d.id)));
  dept.value=profile.department_id == null ? "" : String(profile.department_id);
  const level = document.createElement("select");level.disabled=true;
  level.append(new Option("Not specified", ""));for (const l of [100,200,300,400,500,600]) level.append(new Option(`${l} Level`,String(l)));
  level.value=profile.academic_level == null ? "" : String(profile.academic_level);
  const student = profile.role === "student" || profile.role === "lecturer";
  function field(label, control) { const box=make("label", "pf-field"); box.append(make("span", "", label),control);return box; }
  const fields=make("div", "pf-fields");fields.append(field("Full Name",name),field("Email Address",email),field("Account Role",role),field("Institution", institution));
  if(student){fields.append(field("Department",dept));if(profile.role==="student")fields.append(field("Academic Level",level));}
  form.append(fields);
  if(student)form.append(make("p", "pf-hint", "Your department and academic level determine which newly published resources you are notified about. Choose your actual academic details."));
  else form.append(make("p", "pf-hint", "Academic affiliation is managed by administrators for this account role."));
  const feedback=make("p", "pf-message");feedback.setAttribute("aria-live","polite");
  const controls=make("div", "pf-actions");const save=make("button", "pf-button", "Save Changes");save.type="submit";save.hidden=true;
  const cancel=make("button", "pf-button pf-secondary", "Cancel");cancel.type="button";cancel.hidden=true;controls.append(cancel,save);
  form.append(feedback,controls);personal.append(form);grid.append(personal);
  const security=make("section", "pf-card");security.append(make("h2", "", "Password & Security"),make("p", "pf-card-desc", "Keep your library account secure."));
  security.append(make("p", "pf-hint", "Password changes are not available through the current profile API. Contact your library administrator if you need to reset your password."));grid.append(security);
  const info=make("section", "pf-card");info.append(make("h2", "", "Account Information"));
  const values=make("dl", "pf-details");for(const [k,v] of [["Account Status",profile.is_active?"Active":"Inactive"],["Access Level",statusText(profile.role)],["Department", departmentName()],["Institution","UNN"]]){values.append(make("dt","",k),make("dd","",v));}
  info.append(values);grid.append(info);
  let editing=false;
  function setEditing(value){editing=value;name.disabled=!value;dept.disabled=!value || !student || departments.length===0;level.disabled=!value || profile.role!=="student";save.hidden=!value;cancel.hidden=!value;edit.hidden=value;feedback.textContent="";}
  edit.addEventListener("click",()=>setEditing(true));
  cancel.addEventListener("click",()=>{name.value=profile.full_name||"";dept.value=profile.department_id==null?"":String(profile.department_id);level.value=profile.academic_level==null?"":String(profile.academic_level);setEditing(false);});
  form.addEventListener("submit",async ev=>{
    ev.preventDefault();if(!editing)return;
    const payload={full_name:name.value.trim()};
    if(!payload.full_name){feedback.textContent="Enter your full name.";return;}
    if(student && departments.length){payload.department_id=dept.value?Number(dept.value):null;}
    if(profile.role==="student")payload.academic_level=level.value?Number(level.value):null;
    save.disabled=true;feedback.textContent="Saving profile…";
    try{
      profile=await apiRequest("/auth/me",{method:"PATCH",body:JSON.stringify(payload)});
      person.querySelector("strong").textContent=profile.full_name;
      avatar.textContent=(profile.full_name||"U").slice(0,2).toUpperCase();
      for(const dd of values.querySelectorAll("dd")){if(dd.previousSibling?.textContent==="Department")dd.textContent=departmentName();}
      onSaved?.(profile);setEditing(false);feedback.textContent="Profile updated successfully.";
    }catch(err){feedback.classList.add("pf-error");feedback.textContent=`Could not update profile: ${err.message}`;}
    finally{save.disabled=false;}
  });
}

# -*- coding: utf-8 -*-
from odoo import models, fields, api

class StakeholderTeamMember(models.Model):
    _name = 'stakeholder.team.member'
    _description = 'Association Team Member'

    partner_id = fields.Many2one('res.partner', string='Organisation/Association', ondelete='cascade')
    name = fields.Char(string='Name', required=True)
    designation = fields.Selection([
        ('president', 'President'),
        ('vp', 'Vice President'),
        ('secretary', 'Secretary'),
        ('joint_secretary', 'Joint Secretary'),
        ('treasurer', 'Treasurer'),
        ('joint_treasurer', 'Joint Treasurer'),
        ('ec_member', 'E.C. Member'),
    ], string='Designation', required=True)
    phone = fields.Char(string='Phone')
    email = fields.Char(string='Email')

class StakeholderBoardMember(models.Model):
    _name = 'stakeholder.board.member'
    _description = 'Organisation Board Member'

    partner_id = fields.Many2one('res.partner', string='Organisation/Institution', ondelete='cascade')
    name = fields.Char(string='Member Name', required=True)
    designation = fields.Char(string='Designation', required=True)
    phone = fields.Char(string='Phone')
    email = fields.Char(string='Email')

class StakeholderDeptHead(models.Model):
    _name = 'stakeholder.dept.head'
    _description = 'Key Department Head'

    partner_id = fields.Many2one('res.partner', string='Organisation/Institution', ondelete='cascade')
    name = fields.Char(string='Name', required=True)
    designation = fields.Char(string='Designation', required=True)
    phone = fields.Char(string='Phone')
    email = fields.Char(string='Email')

class StakeholderOrganisationAssociation(models.Model):
    _name = 'stakeholder.organisation.association'
    _description = 'Organisation Association Membership'

    partner_id = fields.Many2one('res.partner', string='Organisation/Institution', ondelete='cascade')
    association_id = fields.Many2one('stakeholder.association',string='Association Name', required=True)
    membership_number = fields.Char(string='Membership Number')
    expiry_date = fields.Date(string='Expiry Date')

# stakeholder.facility and stakeholder.skill.program are defined in stakeholder_registration module

class StudentHealthProfile(models.Model):
    _name = 'student.health.profile'
    _description = 'Student Health Profile'

    name = fields.Char(string='Profile Name', compute='_compute_name')
    blood_group = fields.Selection([
        ('A+', 'A+'), ('A-', 'A-'),
        ('B+', 'B+'), ('B-', 'B-'),
        ('O+', 'O+'), ('O-', 'O-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'),
    ], string='Blood Group')
    allergies = fields.Text(string='Allergies')
    medical_history = fields.Text(string='Medical History/Conditions')
    vaccination_status = fields.Text(string='Vaccination Status')
    height = fields.Float(string='Height (cm)')
    weight = fields.Float(string='Weight (kg)')

    @api.depends('blood_group')
    def _compute_name(self):
        for record in self:
            record.name = f"Health Info ({record.blood_group or 'Unknown'})"

class StudentAchievement(models.Model):
    _name = 'student.achievement'
    _description = 'Student Activity & Achievement'

    student_profile_id = fields.Many2one('student.profile', string='Student Profile', ondelete='cascade')
    type = fields.Selection([
        ('project', 'Project'),
        ('competition', 'Competition Result'),
        ('badge', 'Badge / Award'),
        ('library', 'Library / Resource Access History')
    ], string='Category', required=True)
    name = fields.Char(string='Title/Description', required=True)
    date = fields.Date(string='Date')
    achievement_details = fields.Text(string='Details')

# Mock models for Parent Portal display
class StudentTimetable(models.Model):
    _name = 'student.timetable'
    _description = 'Student Timetable'

    student_profile_id = fields.Many2one('student.profile', string='Student Profile', ondelete='cascade')
    day = fields.Selection([
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday')
    ], string='Day')
    time_slot = fields.Char(string='Time Slot')
    subject = fields.Char(string='Subject')
    teacher = fields.Char(string='Teacher')
    classroom = fields.Char(string='Classroom')

class StudentAttendance(models.Model):
    _name = 'student.attendance'
    _description = 'Student Attendance'

    student_profile_id = fields.Many2one('student.profile', string='Student Profile', ondelete='cascade')
    date = fields.Date(string='Date', required=True)
    subject = fields.Char(string='Subject')
    status = fields.Selection([
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late')
    ], string='Status', default='present')
    leave_applied = fields.Boolean(string='Leave Applied', default=False)
    leave_status = fields.Selection([
        ('draft', 'Draft/Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], string='Leave Approval Status')

class StudentExam(models.Model):
    _name = 'student.exam'
    _description = 'Student Exams'

    student_profile_id = fields.Many2one('student.profile', string='Student Profile', ondelete='cascade')
    exam_date = fields.Date(string='Exam Date', required=True)
    subject = fields.Char(string='Subject', required=True)
    syllabus = fields.Text(string='Syllabus')
    rubrics = fields.Text(string='Assessment Rubrics')

class StudentCircular(models.Model):
    _name = 'student.circular'
    _description = 'School Circular'

    name = fields.Char(string='Title', required=True)
    date = fields.Date(string='Date', default=fields.Date.today)
    content = fields.Text(string='Content')
    category = fields.Selection([
        ('general', 'General Announcement'),
        ('event', 'Holiday / Event'),
        ('urgent', 'Urgent Notice')
    ], string='Category', default='general')

class StudentResource(models.Model):
    _name = 'student.resource'
    _description = 'Parenting & Support Resources'

    name = fields.Char(string='Title', required=True)
    author = fields.Char(string='Author/Expert')
    category = fields.Selection([
        ('article', 'Article'),
        ('webinar', 'Webinar'),
        ('workshop', 'Expert Workshop')
    ], string='Resource Type', required=True)
    article_type = fields.Selection([
        ('psychology', 'Child Psychology'),
        ('nutrition', 'Nutrition'),
        ('study_habits', 'Study Habits'),
        ('other', 'General Support')
    ], string='Focus Area', default='other')
    content = fields.Text(string='Summary/Content')
    link = fields.Char(string='Resource Link')

class StudentGrade(models.Model):
    _name = 'student.grade'
    _description = 'Student Academic Grade/Marks'

    student_profile_id = fields.Many2one('student.profile', string='Student Profile', ondelete='cascade')
    term = fields.Char(string='Term/Exam', required=True)
    subject = fields.Char(string='Subject', required=True)
    marks_obtained = fields.Float(string='Marks Obtained')
    max_marks = fields.Float(string='Max Marks', default=100.0)
    grade = fields.Char(string='Grade')
    feedback = fields.Text(string='Teacher Feedback')

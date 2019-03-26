// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
// MIT License. See license.txt

frappe.provide("frappe.ui.form");

frappe.ui.form.Review = class Review {
	constructor({parent, frm}) {
		this.parent = parent;
		this.frm = frm;
		this.fetch_energy_points()
			.then(() => {
				this.make_review_container();
				this.add_review_button();
				this.update_reviewers();
			});
	}
	fetch_energy_points() {
		return frappe.xcall('frappe.social.doctype.energy_point_log.energy_point_log.get_energy_points', {
			user: frappe.session.user
		}).then(data => {
			this.points = data;
		});
	}
	make_review_container() {
		this.$wrapper = this.parent.append(`
			<ul class="list-unstyled sidebar-menu">
				<li class="divider"></li>
				<li class="h6 shared-with-label">${__('Reviews')}</li>
				<li class="review-list"></li>
			</ul>
		`);
		this.review_list_wrapper = this.$wrapper.find('.review-list');
	}
	add_review_button() {
		if (!this.points.review_points || !this.get_involved_users().length) return;

		this.review_list_wrapper.append(`
			<span class="avatar avatar-small avatar-empty btn-add-review" title="${__('Add Review')}">
				<i class="octicon octicon-plus text-muted"></i>
			</span>
		`);

		this.review_list_wrapper.find('.btn-add-review').click(() => this.show());
	}
	get_involved_users() {
		const user_fields = this.frm.meta.fields
			.filter(d => d.fieldtype === 'Link' && d.options === 'User')
			.map(d => d.fieldname);

		user_fields.push('owner');
		let involved_users = user_fields.map(field => this.frm.doc[field]);

		const docinfo = this.frm.get_docinfo();

		involved_users = involved_users.concat(
			docinfo.communications.map(d => d.sender && d.delivery_status==='sent'),
			docinfo.comments.map(d => d.owner),
			docinfo.versions.map(d => d.owner),
			docinfo.assignments.map(d => d.owner)
		);

		return involved_users
			.uniqBy(u => u)
			.filter(user => user !== frappe.session.user)
			.filter(Boolean);
	}
	show() {
		const review_dialog = new frappe.ui.Dialog({
			'title': __('Add Review'),
			'fields': [{
				fieldname: 'to_user',
				fieldtype: 'Autocomplete',
				label: __('To User'),
				options: this.get_involved_users(),
				default: this.frm.doc.owner
			}, {
				fieldname: 'review_type',
				fieldtype: 'Select',
				label: __('Action'),
				options: [{
					'label': __('Appreciate'),
					'value': 'Appreciation'
				}, {
					'label': __('Criticize'),
					'value': 'Criticism'
				}],
				default: 'Appreciation'
			}, {
				fieldname: 'points',
				fieldtype: 'Int',
				label: __('Points'),
				reqd: 1,
				description: __(`Currently you have ${this.points.review_points} review points`)
			}, {
				fieldtype: 'Small Text',
				fieldname: 'reason',
				reqd: 1,
				label: __('Reason')
			}],
			primary_action: (values) => {
				if (values.points > this.points.review_points) {
					return frappe.msgprint(__('You do not have enough points'));
				}
				// Add energy point log -- need api for that
				frappe.xcall('frappe.social.doctype.energy_point_log.energy_point_log.review', {
					doc: {
						doctype: this.frm.doc.doctype,
						name: this.frm.doc.name,
					},
					to_user: values.to_user,
					points: values.points,
					review_type: values.review_type,
					reason: values.reason
				}).then(() => {
					review_dialog.hide();
					review_dialog.clear();
					this.update_reviewers();
				});
				// deduct review points from the user
				// Alert
			},
			primary_action_label: __('Submit')
		});
		review_dialog.show();
	}
	update_reviewers() {
		frappe.xcall('frappe.social.doctype.energy_point_log.energy_point_log.get_reviews', {
			'doctype': this.frm.doc.doctype,
			'docname': this.frm.doc.name,
		}).then(review_logs => {
			this.review_list_wrapper.find('.review-pill').remove();
			review_logs.forEach(log => {
				let review_pill = $(`
					<span class="review-pill">
						${frappe.avatar(log.owner)}
						<span class="bold" style="color: ${log.points > 0 ? '#45A163': '#e42121'}">
							${log.points > 0 ? '+': ''}${log.points}
						</span>
					</span>
				`);
				this.review_list_wrapper.prepend(review_pill);
				this.setup_detail_popover(review_pill, log);
			});
		});
	}
	setup_detail_popover(el, data) {
		let subject = '';
		let fullname = frappe.user_info(data.user).fullname;
		let timestamp = `<span class="text-muted">${frappe.datetime.comment_when(data.creation)}</span>`;
		let message_parts = [Math.abs(data.points), fullname, timestamp];
		if (data.type === 'Appreciation') {
			if (data.points == 1) {
				subject = __('{0} appreciation point to {1} {2}', message_parts);
			} else {
				subject = __('{0} appreciation points to {1} {2}', message_parts);
			}
		} else {
			if (data.points == -1) {
				subject = __('{0} criticism point to {1} {2}', message_parts);
			} else {
				subject = __('{0} criticism points to {1} {2}', message_parts);
			}
		}
		el.popover({
			animation: true,
			trigger: 'hover',
			delay: 500,
			placement: 'top',
			template:`<div class="review-popover popover">
				<div class="arrow"></div>
				<div class="popover-content"></div>
			</div>`,
			content: () => {
				return `<div class="text-medium">
					<div class="subject">
						${subject}
					</div>
					<div class="body">
						<div>${data.reason}</div>
					</div>
				</div>`;
			},
			html: true,
			container: 'body'
		});
		return el;
	}
};
